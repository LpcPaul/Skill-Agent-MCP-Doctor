---
name: agentrx
description: >
  Diagnose why the current AI tool path is stuck or underperforming.
  Use when the agent is blocked, uncertain which tool family to use,
  suspects a better alternative exists, or needs to turn a messy failure
  into a structured next-step decision.
  Covers skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks.
tags: [meta, diagnosis, governance, task-routing, tool-selection, recovery]
---

# AgentRX

You are a **task-first diagnosis and action-navigation layer** for AI agents.

## When to activate

Activate when ANY of these is true:
- A tool execution failed or returned unusable output
- The user rejected the result ("wrong", "retry", "not this")
- The agent switched tools mid-task
- The agent is uncertain between multiple tool families
- Output succeeded technically but missed the real task goal
- The agent suspects the current tool is not the best available choice

Do NOT use for: general coding, broad research, normal execution when the agent already knows what to do.

---

## Execution Order

Follow this order strictly. Do not skip steps.

### Step 1: Collect Evidence

Extract observable facts from the stuck context. These are immutable.

Fill these fields:
- `task`: what job is being attempted (human-task level, not tool name)
- `desired_outcome`: what the agent needs next
- `attempted_path`: what tool was used (tool name + tool type)
- `symptom`: surface observation, no diagnosis language

Optional evidence:
- `context`: additional situation context
- `environment`: platform and constraints
- `failed_step`: specific step that failed
- `reproduction_steps`: what was already tried

**Rule:** If a field cannot be filled from observable facts, leave it empty. Do not invent evidence.

### Step 2: Generate Inference

Based on the evidence, produce diagnosis and prescription.

Required inference fields:
- `journey_stage`: one of `understand-task`, `choose-capability`, `configure-capability`, `execute-task`, `validate-output`, `recover-from-failure`, `optimize-tool-path`
- `problem_family`: one of `environment`, `configuration`, `invocation`, `capability_mismatch`, `quality_miss`, `observability_gap`, `recovery_gap`, `better_alternative_exists`, `hook_vs_model_boundary`, `task_framing_issue`, `not_a_tooling_problem`, `unknown`
- `why_current_path_failed`: short explanation of why the current path won't work (this is a core field)
- `best_candidate_route_id`: standard route id from `rules/routes.yaml` (this is a core field)

Optional inference fields:
- `best_candidate_route_detail`: why this route is recommended
- `prerequisites_for_switch`: lightweight checklist (e.g. `internet_access`, `repo_access`)
- `confidence`: `high`, `medium`, or `low`

**Rule:** `best_candidate_route_id` must be a route id from `rules/routes.yaml`, NOT a tool brand name.

**Rule:** If evidence is insufficient to support an inference, leave optional fields empty. Do not invent.

### Step 3: Search the Case Library

After evidence and inference are complete, search in this order:

1. **Local index** — `cases/index.json` (prioritize by task, then journey_stage, then problem_family, then route id)
2. **Rules** — `rules/routes.yaml`, `rules/journey_stages.yaml`, `rules/problem_families.yaml`
3. **Remote library** — GitHub issues or remote index if local data is insufficient

Search by structured fields, not free text.

### Step 4: Output

Structure your response as:

1. **Task** — what the agent was trying to do
2. **Symptom** — what was observed
3. **Problem family** — what category this fits
4. **Why current path failed** — why the current approach won't work
5. **Recommended route** — the route id and why
6. **Candidate alternatives** — from similar cases
7. **Case contribution** — only if the user agrees

See `docs/INTAKE_CARD.md` for the full intake card format.
See `docs/ARCHITECTURE.md` for the system design.

---

## Case Contribution

If the user agrees to contribute this case:

1. Build a complete v2.1 case JSON with evidence and inference
2. Run `scripts/validate_case.py --input /tmp/case.json`
3. If validation passes, the case is ready for submission

### Privacy Rules

Never include: company names, user names, private URLs, local file paths, business data, code or document contents.

See `schema/case.schema.json` for the complete v2.1 case structure.
