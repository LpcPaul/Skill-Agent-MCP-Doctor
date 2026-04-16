#!/usr/bin/env python3
"""
AgentRX — Build Index Script

Reads all case JSON files and generates cases/index.json.
Compatible with both v2.0 (flat) and v2.1 (evidence/inference) structures.

Usage:
    python3 scripts/build_index.py [--input-dir cases/] [--output cases/index.json]

The index contains:
- schema_versions: list of schema versions present
- case_count: total number of cases
- task_categories: unique tasks
- route_ids: unique route ids from inference
- problem_families: unique problem families
- journey_stages: unique journey stages
- cases: lightweight entries for retrieval
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).parent.parent


def normalize_case(case: dict) -> dict:
    """Normalize any case version to a common dict for indexing."""
    if case.get("schema_version") == "2.1":
        return case

    # v2.0 flat structure normalization
    return {
        "schema_version": case.get("schema_version", "2.0"),
        "id": case.get("case_id", case.get("id", "unknown")),
        "title": case.get("title", f"{case.get('task_category', 'unknown')} {case.get('journey_stage', 'unknown')} {case.get('suspected_problem_family', 'unknown')}"),
        "summary": case.get("diagnosis_summary", case.get("recommendation_detail", "")),
        "tags": case.get("tags", []),
        "evidence": {
            "task": case.get("task_category", ""),
            "desired_outcome": case.get("task_goal", case.get("desired_outcome", "")),
            "attempted_path": case.get("tool_triggered", ""),
            "symptom": case.get("observed_symptom", ""),
        },
        "inference": {
            "journey_stage": case.get("journey_stage", "unknown"),
            "problem_family": case.get("suspected_problem_family", "unknown"),
            "why_current_path_failed": case.get("diagnosis_summary", ""),
            "best_candidate_route_id": map_next_step_to_route(case.get("recommended_next_step", "")),
            "confidence": case.get("confidence", "medium"),
        },
        "resolution": {
            "outcome": case.get("outcome", "unknown"),
        },
    }


def map_next_step_to_route(next_step: str) -> str:
    """Map v2.0 recommended_next_step to v2.1 route id."""
    mapping = {
        "switch_tool_within_same_task": "switch_to_alternative_tool_path",
        "adjust_current_tool_invocation": "switch_to_alternative_tool_path",
        "inspect_environment_or_permissions": "switch_to_environment_debugging",
        "move_to_hook_or_workflow": "decompose_task_first",
        "reframe_task_before_retry": "request_missing_input",
        "ask_for_one_missing_constraint": "request_missing_input",
        "stop_tooling_changes_not_a_tool_issue": "request_missing_input",
        "other": "switch_to_alternative_tool_path",
    }
    return mapping.get(next_step, "switch_to_alternative_tool_path")


def build_index_entry(case: dict) -> dict:
    """Build a lightweight index entry from a normalized case."""
    evidence = case.get("evidence", {})
    inference = case.get("inference", {})
    resolution = case.get("resolution", {})

    # Build searchable text from key fields
    searchable_parts = [
        evidence.get("task", ""),
        evidence.get("desired_outcome", ""),
        evidence.get("attempted_path", {}).get("tool", "") if isinstance(evidence.get("attempted_path"), dict) else str(evidence.get("attempted_path", "")),
        evidence.get("symptom", ""),
        inference.get("journey_stage", ""),
        inference.get("problem_family", ""),
        inference.get("why_current_path_failed", ""),
        inference.get("best_candidate_route_id", ""),
        inference.get("best_candidate_route_detail", ""),
        case.get("summary", ""),
        " ".join(case.get("tags", [])),
    ]
    searchable_text = " ".join(p for p in searchable_parts if p)

    # Get attempted_path as string
    ap = evidence.get("attempted_path", {})
    if isinstance(ap, dict):
        attempted_path = ap.get("tool", "")
    else:
        attempted_path = str(ap)

    return {
        "id": case.get("id", "unknown"),
        "title": case.get("title", ""),
        "summary": case.get("summary", ""),
        "schema_version": case.get("schema_version", "unknown"),
        "task": evidence.get("task", ""),
        "desired_outcome": evidence.get("desired_outcome", ""),
        "attempted_path": attempted_path,
        "symptom": evidence.get("symptom", ""),
        "journey_stage": inference.get("journey_stage", "unknown"),
        "problem_family": inference.get("problem_family", "unknown"),
        "why_current_path_failed": inference.get("why_current_path_failed", ""),
        "best_candidate_route_id": inference.get("best_candidate_route_id", ""),
        "confidence": inference.get("confidence", "medium"),
        "outcome": resolution.get("outcome", "unknown"),
        "tags": case.get("tags", []),
        "searchable_text": searchable_text,
    }


def main():
    parser = argparse.ArgumentParser(description="Build AgentRX case index")
    parser.add_argument("--input-dir", default=str(REPO_ROOT / "cases"), help="Directory to scan for case files")
    parser.add_argument("--output", default=str(REPO_ROOT / "cases" / "index.json"), help="Output index file path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    # Collect all case files
    case_files = []
    for f in sorted(input_dir.rglob("*.json")):
        # Skip index.json itself and template files
        if f.name == "index.json" or "templates" in str(f) or f.stem.startswith("."):
            continue
        case_files.append(f)

    # Process cases
    all_entries = []
    schema_versions = set()
    task_categories = set()
    route_ids = set()
    problem_families = set()
    journey_stages = set()
    route_counts = defaultdict(int)

    for cf in case_files:
        try:
            with open(cf) as f:
                raw = json.load(f)

            # Handle array of cases (legacy format)
            if isinstance(raw, list):
                cases = raw
            elif isinstance(raw, dict):
                cases = [raw]
            else:
                print(f"  SKIP {cf.name}: unexpected format")
                continue

            for case in cases:
                normalized = normalize_case(case)
                schema_versions.add(normalized.get("schema_version", "unknown"))

                evidence = normalized.get("evidence", {})
                inference = normalized.get("inference", {})

                task_categories.add(evidence.get("task", ""))
                route_ids.add(inference.get("best_candidate_route_id", ""))
                problem_families.add(inference.get("problem_family", ""))
                journey_stages.add(inference.get("journey_stage", ""))

                route_id = inference.get("best_candidate_route_id", "")
                if route_id:
                    route_counts[route_id] += 1

                all_entries.append(build_index_entry(normalized))

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  SKIP {cf.name}: {e}")
            continue

    # Clean up empty strings
    task_categories.discard("")
    route_ids.discard("")
    problem_families.discard("")
    journey_stages.discard("")

    # Build index
    index = {
        "schema_version": "2.1",
        "project_name": "agentrx",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "navigation_order": [
            "task",
            "journey_stage",
            "problem_family",
            "best_candidate_route_id",
        ],
        "schema_versions": sorted(schema_versions),
        "task_categories": sorted(task_categories),
        "route_ids": sorted(route_ids),
        "route_counts": dict(sorted(route_counts.items())),
        "problem_families": sorted(problem_families),
        "journey_stages": sorted(journey_stages),
        "case_count": len(all_entries),
        "cases": all_entries,
    }

    with open(output_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"Index built: {output_path}")
    print(f"  Cases: {len(all_entries)}")
    print(f"  Schema versions: {sorted(schema_versions)}")
    print(f"  Tasks: {len(task_categories)}")
    print(f"  Route ids: {len(route_ids)}")
    print(f"  Problem families: {len(problem_families)}")
    print(f"  Journey stages: {len(journey_stages)}")


if __name__ == "__main__":
    main()
