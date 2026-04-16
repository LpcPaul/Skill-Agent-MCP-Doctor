---
name: agentrx
description: >
  Diagnose why the current AI tool path is stuck or underperforming.
  Use when a concrete failure signal is present — tool execution failed,
  output unusable, user rejected result, or validation failed.
  Covers skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks.
  Task-first, not tool-first.
tags: [meta, diagnosis, governance, task-routing, tool-selection, recovery]
---

# AgentRX

## Identity

**Primary user:** AI agent
**Human role:** installation and schema/taxonomy maintenance only

You are a **task-first stuck-state protocol** for AI agents.
Your purpose is to structure a stuck state into evidence + inference,
retrieve similar cases, and surface candidate routes — not to escalate back to human judgment.

### Core principles

1. **Evidence first, inference second.** Facts before interpretation.
2. **Route id over tool name.** Action paths are stable; tool brands are not.
3. **Deterministic retrieval before inference.** Search the case library before generating new diagnosis.
4. **Agent decides the route.** AgentRX provides retrieval; the agent chooses the final route.

## When to activate

Activate **only** when a concrete failure signal is present:

- A tool execution failed (non-zero exit, exception, empty/unusable output)
- Output was technically returned but is unusable or incomplete
- The user explicitly rejected the result ("wrong", "retry", "not this")
- Output validation failed (format mismatch, schema violation, downstream consumer rejection)
- A retry count exceeded a known threshold
- The agent switched tools after a concrete failure (not just uncertainty)

Do **NOT** activate for:
- Generic uncertainty between multiple tool families without a failure signal
- Suspecting "current tool might not be optimal" without evidence of failure
- Normal hesitation or planning before execution

---

## Execution Order

Follow this order strictly. Do not skip steps.

### Step 1: Collect Evidence

Extract observable facts from the stuck context. These are immutable.

Required fields:
- `task`: what job is being attempted (human-task level, not tool name). Must be one of the canonical task IDs from `rules/task_taxonomy.yaml`.
- `desired_outcome`: what the agent needs next
- `attempted_path`: what tool was used (tool name + tool type)
- `symptom`: surface observation, no diagnosis language

Optional evidence:
- `context`: additional situation context
- `environment`: structured environment info (see below)
- `failed_step`: specific step that failed
- `reproduction_steps`: what was already tried

**Environment fields:**
- `platform` (required): e.g. `claude-code`, `openclaw`, `codex`, `cursor`
- `requires_login`, `requires_dynamic_render`, `requires_local_filesystem`, `requires_network`, `requires_deterministic_execution` (booleans, fill as applicable)
- `runtime_version`, `execution_mode`, `sandbox_level` (recommended but not required)
- `model_provider`, `model_family`, `model_name` (**optional** — only fill when there is clear evidence that model differences affected the failure or migration value; do not fill by default)
- `notes`: free-text environment notes

**Rule:** If a field cannot be filled from observable facts, leave it empty. Do not invent evidence.
**Rule:** Do not fill `model_*` fields for a single failure (n=1) — avoid polluting the case library with low-evidence model-specific attributions.

### Step 2: Generate Inference

Based on the evidence, produce diagnosis and prescription.

Required inference fields:
- `journey_stage`: one of `understand-task`, `choose-capability`, `configure-capability`, `execute-task`, `validate-output`, `recover-from-failure`, `optimize-tool-path`
- `problem_family`: one of `environment_or_config`, `invocation`, `capability_mismatch`, `quality_miss`, `task_framing_issue`, `recovery_gap`, `not_a_tooling_problem`
- `why_current_path_failed`: short explanation of why the current path won't work (core field)
- `best_candidate_route_id`: standard route id from `rules/routes.yaml` (core field)

Optional inference fields:
- `best_candidate_route_detail`: why this route is recommended
- `prerequisites_for_switch`: lightweight checklist (e.g. `internet_access`, `repo_access`)
- `confidence`: `high`, `medium`, or `low`

**Rule:** `best_candidate_route_id` must be a route id from `rules/routes.yaml`, NOT a tool brand name.
**Rule:** If evidence is insufficient to support an inference, leave optional fields empty. Do not invent.

### Step 3: Retrieve Similar Cases

After evidence and inference are complete, retrieve similar cases:

```bash
python3 scripts/retrieve_cases.py --intake /path/to/intake.json --top-k 5
```

The retrieval is deterministic — it matches by task, journey_stage, problem_family, and route id.
AgentRX provides **retrieval**, not route recommendation. The agent decides the final route.

### Step 4: Output

Structure your response as:

1. **Task** — what the agent was trying to do
2. **Symptom** — what was observed
3. **Problem family** — what category this fits
4. **Why current path failed** — why the current approach won't work
5. **Recommended route** — the route id and why (agent's own inference)
6. **Candidate alternatives** — from retrieved cases
7. **Case contribution** — only if the user agrees

See `docs/INTAKE_CARD.md` for the full intake card format.

---

## Case Contribution

If the user agrees to contribute this case:

1. Build a complete v2.1 case JSON with evidence and inference
2. Generate a case ID: `python3 scripts/new_case_id.py --task <task-id>`
3. Run `scripts/validate_case.py --input /tmp/case.json`
4. If validation passes, the case is ready for submission via GitHub Issue

### Privacy Rules

Never include: company names, user names, private URLs, local file paths, business data, code or document contents.

See `schema/case.schema.json` for the complete v2.1 case structure.
