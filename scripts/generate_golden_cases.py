#!/usr/bin/env python3
"""
AgentRX — Generate Golden (Synthetic Seed) Cases

Creates 10 synthetic seed cases covering the most common stuck states.
Each case uses evidence/inference structure, standard route ids, and realistic detail.

Synthetic seed cases are marked with:
- "source": "synthetic-seed"
- resolution is empty or minimal (outcome: "unknown")
- "verified": false

They must NOT be treated as real solved cases.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = REPO_ROOT / "cases"


def save_case(case: dict, filename: str):
    out = CASES_DIR / filename
    with open(out, "w") as f:
        json.dump(case, f, indent=2, ensure_ascii=False)
    print(f"  Created: {filename}")


def mark_synthetic(case: dict) -> dict:
    """Mark a case as synthetic seed — clear resolution, set source."""
    case["source"] = "synthetic-seed"
    case["verified"] = False
    case["resolution"] = {"outcome": "unknown"}
    if "legacy_mapping" in case:
        del case["legacy_mapping"]
    return case


cases = [
    # ── Case 1: Web research blocked / capability mismatch ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-browse-web-001",
        "title": "browse-web execute-task capability_mismatch",
        "summary": "Agent used a static HTML fetch tool for a dynamically rendered page. Only the shell was captured, missing all content populated by JavaScript.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["browse-web", "execute-task", "capability_mismatch", "dynamic-rendering"],
        "evidence": {
            "task": "browse-web",
            "desired_outcome": "Extract the full product listing table from a retail website.",
            "attempted_path": {
                "tool": "web_fetch",
                "tool_type": "builtin",
            },
            "symptom": "The fetched HTML only contains the page skeleton. All product data loaded via JavaScript is missing.",
            "symptom_tags": ["partial-content", "client-side-rendering"],
            "context": "The target website is a modern single-page application that loads product data via API after the initial HTML loads.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": True,
                "requires_local_filesystem": False,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Static HTML fetch returned page skeleton without JavaScript-rendered content",
            "artifacts_used": ["HTML page", "public URL"],
            "reproduction_steps": [
                "Used web_fetch builtin to retrieve the page",
                "Parsed HTML — found only skeleton structure, no product data",
                "Retried with same approach — same result"
            ]
        },
        "inference": {
            "journey_stage": "execute-task",
            "problem_family": "capability_mismatch",
            "why_current_path_failed": "The builtin fetch tool retrieves static HTML only. The product data on this page is rendered client-side via JavaScript, which static fetch cannot execute.",
            "best_candidate_route_id": "switch_to_alternative_tool_path",
            "best_candidate_route_detail": "Switch to a browser-capable route that executes JavaScript. playwright-mcp can render the page and extract the full DOM.",
            "prerequisites_for_switch": ["internet_access", "repo_access"],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 2: Should switch to official docs ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-code-editing-001",
        "title": "code-editing execute-task environment_or_config",
        "summary": "Agent attempted to integrate a third-party API using guessed parameter names and structure, resulting in repeated authentication errors.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["code-editing", "execute-task", "environment_or_config", "third-party-api"],
        "evidence": {
            "task": "code-editing",
            "desired_outcome": "Integrate a payment gateway API into the existing application.",
            "attempted_path": {"tool": "code-editing", "tool_type": "skill"},
            "symptom": "Repeated API calls fail with authentication errors. The agent has tried different credential formats without success.",
            "symptom_tags": ["api-error", "authentication-failure"],
            "context": "The payment gateway requires a specific authentication flow that differs from the agent's assumptions.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "API authentication fails with 'invalid request format' error",
            "artifacts_used": ["source code", "API credentials"],
            "reproduction_steps": [
                "Attempted integration with assumed authentication pattern",
                "Retried with different credential encoding — same error",
            ]
        },
        "inference": {
            "journey_stage": "execute-task",
            "problem_family": "environment_or_config",
            "why_current_path_failed": "The agent is working from assumptions about API behavior rather than the actual specification.",
            "best_candidate_route_id": "switch_to_official_docs",
            "best_candidate_route_detail": "Fetch the payment gateway's official API documentation to understand the correct authentication flow.",
            "prerequisites_for_switch": ["internet_access"],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 3: Should inspect local files first ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-analyze-data-001",
        "title": "analyze-data understand-task recovery_gap",
        "summary": "Agent tried to analyze data but could not find the source file because it was looking in the wrong directory and using the wrong filename.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["analyze-data", "understand-task", "recovery_gap", "file-location"],
        "evidence": {
            "task": "analyze-data",
            "desired_outcome": "Generate a summary report from a CSV dataset uploaded by the user.",
            "attempted_path": {"tool": "python", "tool_type": "builtin"},
            "symptom": "File not found error. The agent searched for 'data.csv' in the current directory but the file was named 'Q1_results.csv' in a subdirectory.",
            "symptom_tags": ["file-not-found", "wrong-path"],
            "context": "The user uploaded a dataset but did not specify the exact filename or location.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": False,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Attempted to read 'data.csv' — file not found",
            "artifacts_used": ["CSV dataset (undiscovered)"],
            "reproduction_steps": [
                "Tried reading data.csv from root directory",
                "Searched for *.csv in root — found nothing",
            ]
        },
        "inference": {
            "journey_stage": "understand-task",
            "problem_family": "recovery_gap",
            "why_current_path_failed": "The agent has insufficient visibility into the available files.",
            "best_candidate_route_id": "switch_to_local_file_inspection",
            "best_candidate_route_detail": "Run a recursive file listing to discover all available CSV files in the workspace.",
            "prerequisites_for_switch": ["repo_access"],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 4: Missing input ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-create-presentation-001",
        "title": "create-presentation choose-capability task_framing_issue",
        "summary": "Agent was asked to create a presentation but received no content outline, speaker notes, or design preferences.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["create-presentation", "choose-capability", "task_framing_issue", "missing-input"],
        "evidence": {
            "task": "create-presentation",
            "desired_outcome": "Generate a slide deck for a quarterly business review.",
            "attempted_path": {"tool": "pptx-generator", "tool_type": "skill"},
            "symptom": "Every generated slide deck is rejected by the user for being too generic, wrong tone, or missing key metrics.",
            "symptom_tags": ["output-rejected", "generic-content"],
            "context": "The user's request was a single sentence: 'Create a Q4 review deck.' No outline, no data, no design preferences were provided.",
            "environment": {
                "platform": "claude-ai",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": False,
                "requires_network": False,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Generated three different slide deck drafts, all rejected",
            "artifacts_used": [],
            "reproduction_steps": [
                "Generated generic Q4 deck — rejected as too generic",
                "Tried more data-heavy approach — rejected for wrong tone",
            ]
        },
        "inference": {
            "journey_stage": "choose-capability",
            "problem_family": "task_framing_issue",
            "why_current_path_failed": "The task is underspecified. The agent cannot produce a satisfactory presentation without knowing the audience, key metrics, design preferences, or outline.",
            "best_candidate_route_id": "request_missing_input",
            "best_candidate_route_detail": "Ask the user for: (1) key metrics or data points, (2) target audience, (3) preferred tone and design style.",
            "prerequisites_for_switch": [],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 5: Environment debugging ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-code-editing-002",
        "title": "code-editing configure-capability environment_or_config",
        "summary": "Agent repeatedly failed to run a Python script because a required package was not installed in the environment.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["code-editing", "configure-capability", "environment_or_config", "dependency"],
        "evidence": {
            "task": "code-editing",
            "desired_outcome": "Run a data visualization script that uses matplotlib and seaborn.",
            "attempted_path": {"tool": "python", "tool_type": "builtin"},
            "symptom": "ModuleNotFoundError: No module named 'seaborn'. The agent retried the script three times without addressing the missing dependency.",
            "symptom_tags": ["import-error", "missing-dependency"],
            "context": "The script requires matplotlib and seaborn. Only matplotlib was pre-installed.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "python script.py fails with ModuleNotFoundError for seaborn",
            "artifacts_used": ["Python script", "requirements file"],
            "reproduction_steps": [
                "Ran script.py — ModuleNotFoundError: seaborn",
                "Retried — same error",
            ]
        },
        "inference": {
            "journey_stage": "configure-capability",
            "problem_family": "environment_or_config",
            "why_current_path_failed": "The execution environment is missing a required dependency. Retrying the script will not install seaborn.",
            "best_candidate_route_id": "switch_to_environment_debugging",
            "best_candidate_route_detail": "Install the missing seaborn package via pip, or fall back to matplotlib-only visualization.",
            "prerequisites_for_switch": ["repo_access", "internet_access"],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 6: Schema / format validation ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-transform-documents-001",
        "title": "transform-documents validate-output quality_miss",
        "summary": "Agent generated a JSON config file but the output was missing required fields and had incorrect nesting.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["transform-documents", "validate-output", "quality_miss", "json-validation"],
        "evidence": {
            "task": "transform-documents",
            "desired_outcome": "Generate a valid JSON configuration file for a CI/CD pipeline.",
            "attempted_path": {"tool": "code-editing", "tool_type": "skill"},
            "symptom": "The generated JSON file is rejected by the CI/CD system. Missing required 'version' field, and the 'stages' array is nested under the wrong parent key.",
            "symptom_tags": ["schema-invalid", "wrong-structure"],
            "context": "The CI/CD system expects a specific JSON schema with 'version', 'stages', and 'jobs' at the top level.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": False,
                "requires_deterministic_execution": False,
            },
            "failed_step": "CI/CD pipeline rejects config with 'missing required field: version'",
            "artifacts_used": ["JSON config file", "CI/CD schema documentation"],
            "reproduction_steps": [
                "Generated initial JSON config",
                "Pipeline rejected — missing 'version' field",
            ]
        },
        "inference": {
            "journey_stage": "validate-output",
            "problem_family": "quality_miss",
            "why_current_path_failed": "The agent is generating JSON without validating against the target schema.",
            "best_candidate_route_id": "switch_to_schema_or_format_validation",
            "best_candidate_route_detail": "Use the project's CI/CD schema documentation as a template. Validate the output against the schema before submission.",
            "prerequisites_for_switch": [],
            "confidence": "medium"
        },
        "related_cases": [],
    }),

    # ── Case 7: Task should be decomposed first ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-workflow-automation-001",
        "title": "workflow-automation choose-capability capability_mismatch",
        "summary": "Agent was asked to build a full dashboard application in one task. It produced a partial implementation that mixed frontend, backend, and data pipeline code.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["workflow-automation", "choose-capability", "capability_mismatch", "complex-task"],
        "evidence": {
            "task": "workflow-automation",
            "desired_outcome": "Build a data dashboard with charts, filters, and a backend API serving live metrics.",
            "attempted_path": {"tool": "code-editing", "tool_type": "skill"},
            "symptom": "The generated code mixes frontend components, API routes, and data transformation logic in a single file. The result is incomplete and unrunnable.",
            "symptom_tags": ["mixed-concerns", "incomplete-implementation"],
            "context": "The dashboard requires three distinct components: (1) frontend UI, (2) backend API, (3) data processing pipeline.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Generated monolithic code that cannot be run as-is",
            "artifacts_used": ["partial code output"],
            "reproduction_steps": [
                "Generated full-stack code in one file — unrunnable",
                "Attempted to split into components mid-generation — structure became inconsistent",
            ]
        },
        "inference": {
            "journey_stage": "choose-capability",
            "problem_family": "capability_mismatch",
            "why_current_path_failed": "The task is too large for a single tool path. The agent needs to decompose it into independent sub-tasks.",
            "best_candidate_route_id": "decompose_task_first",
            "best_candidate_route_detail": "Split into three phases: (1) Design the data model and API contract, (2) Build the backend API, (3) Build the frontend.",
            "prerequisites_for_switch": [],
            "confidence": "high"
        },
        "related_cases": [],
    }),

    # ── Case 8: Should use targeted web research ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-search-and-compare-tools-001",
        "title": "search-and-compare-tools understand-task capability_mismatch",
        "summary": "Agent used a general web search to find technical API documentation, but the search results returned blog posts and tutorials instead of authoritative references.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["search-and-compare-tools", "understand-task", "capability_mismatch", "web-research"],
        "evidence": {
            "task": "search-and-compare-tools",
            "desired_outcome": "Find the correct method signature for a specific library function.",
            "attempted_path": {"tool": "tavily", "tool_type": "skill"},
            "symptom": "Web search returns blog posts and StackOverflow answers from 2022, which reference deprecated method signatures.",
            "symptom_tags": ["outdated-results", "wrong-result-type"],
            "context": "The library was recently updated with breaking changes. General web search favors popular but outdated content.",
            "environment": {
                "platform": "claude-ai",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": False,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Web search returned outdated tutorial content, not current API reference",
            "artifacts_used": ["search query"],
            "reproduction_steps": [
                "Searched for method signature using general web search",
                "Retried with more specific query — still got outdated results",
            ]
        },
        "inference": {
            "journey_stage": "understand-task",
            "problem_family": "capability_mismatch",
            "why_current_path_failed": "General web search is not the right tool for finding authoritative API documentation.",
            "best_candidate_route_id": "switch_to_web_research",
            "best_candidate_route_detail": "Search specifically for the library's official documentation site, or use web_fetch to directly access the library's docs URL.",
            "prerequisites_for_switch": ["internet_access"],
            "confidence": "medium"
        },
        "related_cases": [],
    }),

    # ── Case 9: Reproduction minimization needed ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-code-editing-003",
        "title": "code-editing recover-from-failure recovery_gap",
        "summary": "Agent encountered an intermittent test failure that only reproduces 30% of the time.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["code-editing", "recover-from-failure", "recovery_gap", "flaky-test"],
        "evidence": {
            "task": "code-editing",
            "desired_outcome": "Fix a failing unit test in the authentication module.",
            "attempted_path": {"tool": "code-editing", "tool_type": "skill"},
            "symptom": "The test fails intermittently — approximately 30% of runs produce a timeout error.",
            "symptom_tags": ["intermittent-failure", "timeout"],
            "context": "The test involves an async HTTP call with a 5-second timeout. Network latency may be a factor.",
            "environment": {
                "platform": "claude-code",
                "requires_login": False,
                "requires_dynamic_render": False,
                "requires_local_filesystem": True,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Unit test times out intermittently (~30% failure rate)",
            "artifacts_used": ["test file", "source code"],
            "reproduction_steps": [
                "Ran test 5 times — failed 2 times with timeout",
                "Modified retry logic — passed 3 times, failed 2 times",
            ]
        },
        "inference": {
            "journey_stage": "recover-from-failure",
            "problem_family": "recovery_gap",
            "why_current_path_failed": "The intermittent nature of the failure makes it impossible to determine if a code change actually fixed the issue.",
            "best_candidate_route_id": "switch_to_repro_minimization",
            "best_candidate_route_detail": "Create a minimal reproduction script that isolates the async HTTP call and runs it repeatedly to confirm the failure pattern.",
            "prerequisites_for_switch": ["repo_access"],
            "confidence": "medium"
        },
        "related_cases": [],
    }),

    # ── Case 10: API or connector access needed ──
    mark_synthetic({
        "schema_version": "2.1",
        "id": "2026-04-17-monitor-and-check-001",
        "title": "monitor-and-check execute-task capability_mismatch",
        "summary": "Agent attempted to monitor a cloud service's status by scraping a public status page, but the page structure changed and the scraper broke.",
        "created_at": "2026-04-17T00:00:00Z",
        "tags": ["monitor-and-check", "execute-task", "capability_mismatch", "status-monitoring"],
        "evidence": {
            "task": "monitor-and-check",
            "desired_outcome": "Monitor the operational status of a cloud service and alert on incidents.",
            "attempted_path": {"tool": "browser-cdp", "tool_type": "skill"},
            "symptom": "The web scraper broke after the status page was redesigned. The CSS selectors no longer match.",
            "symptom_tags": ["scraper-broken", "brittle-automation"],
            "context": "The service provider offers an official status API with structured incident data.",
            "environment": {
                "platform": "openclaw",
                "requires_login": False,
                "requires_dynamic_render": True,
                "requires_local_filesystem": False,
                "requires_network": True,
                "requires_deterministic_execution": False,
            },
            "failed_step": "Web scraper CSS selectors no longer match redesigned status page",
            "artifacts_used": ["scraper script", "status page URL"],
            "reproduction_steps": [
                "Ran scraper — selectors failed to match",
                "Updated selectors for new page structure — different elements broke next day",
            ]
        },
        "inference": {
            "journey_stage": "execute-task",
            "problem_family": "capability_mismatch",
            "why_current_path_failed": "Web scraping a status page is a fragile approach. The page structure can change at any time.",
            "best_candidate_route_id": "switch_to_api_or_connector_access",
            "best_candidate_route_detail": "Configure the cloud-status-api-mcp connector using the available API key for structured, stable data.",
            "prerequisites_for_switch": ["api_credentials_available", "internet_access"],
            "confidence": "high"
        },
        "related_cases": [],
    }),
]

# Save each case as a separate file
for case in cases:
    filename = f"{case['id']}.json"
    save_case(case, filename)

print(f"\nGenerated {len(cases)} synthetic seed cases")
print(f"Route coverage:")
route_ids = sorted(set(c['inference']['best_candidate_route_id'] for c in cases))
for rid in route_ids:
    count = sum(1 for c in cases if c['inference']['best_candidate_route_id'] == rid)
    print(f"  {rid}: {count} case(s)")
