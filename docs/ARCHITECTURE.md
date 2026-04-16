# Architecture — AgentRX v2.1

## One sentence summary

AgentRX is a **stuck-state navigation system** for AI agents.

It is not a case database for humans.
It is a machine-to-machine knowledge layer that turns messy failures into structured next-step decisions.

## Audience

**Primary runtime consumer: AI agents**

The system is designed for AI agents to read, navigate, and contribute cases.
The case library, schema, and route registry are all machine-consumable first.

**Human role: installer, repository host, and occasional maintainer**

This is not "primary user, secondary user." It is:
- AI runs the system.
- Humans install it, host the repository, and maintain the schema and rules.

The repository may be discovered by humans, but the runtime consumer is AI.

### Why README still starts with human pain

Installation is a human decision; operation is not.

The README first screen serves humans deciding whether to install.
The system itself serves AI agents after installation.
These are two different audiences with two different purposes, and the narrative handles both without conflating them.

## The old approach (v1)

The v1 architecture assumed the agent could answer:
- which tool was involved
- what failure label applies

This worked for simple cases but failed for real stuck states:
- Agents feel symptoms first, not diagnoses
- "page incomplete" is a symptom, not a failure type
- The agent often doesn't know which tool to blame yet

## The new approach (v2.1)

```text
stuck state
  -> collect evidence (immutable facts)
  -> generate inference (diagnosis + prescription)
  -> search case library by task + stage + problem family
  -> retrieve similar cases and route recommendations
  -> choose next action
  -> optional: contribute this case back
```

## Case Object: Two Layers

Every case is split into two layers:

### Evidence Layer (immutable)

Facts extracted directly from the stuck context:
- `task`: what job was being attempted
- `desired_outcome`: what the agent needed
- `attempted_path`: what tool path was used
- `symptom`: what was observed
- `context`, `environment`, `failed_step`, `reproduction_steps`

These fields are **observations**, not interpretations.
They should be the same regardless of which AI reads them.

### Inference Layer (re-computable)

AI-generated diagnosis and prescription:
- `journey_stage`: where the blockage is
- `problem_family`: what category it fits
- `why_current_path_failed`: why the current path won't work
- `best_candidate_route_id`: which action path to take next
- `confidence`: how sure the AI is

These fields are **interpretations**.
A different AI reading the same evidence might produce different inference.
This is by design — inference is disposable, evidence is permanent.

## Route Registry

`rules/routes.yaml` defines standard **route ids** that `best_candidate_route_id` must reference.

Routes are **action paths**, not tool brands:
- `switch_to_web_research` — not "use Tavily"
- `switch_to_alternative_tool_path` — not "use playwright-mcp"
- `request_missing_input` — not "ask user for API key"

Why this matters:
- Route ids are stable across tool ecosystem changes
- They enable aggregation and statistics ("30% of cases recommend route X")
- They prevent tool-name pollution in the case library
- They make cases future-proof (tools come and go, action patterns persist)

Current routes:
- `switch_to_web_research`
- `switch_to_official_docs`
- `switch_to_local_file_inspection`
- `switch_to_api_or_connector_access`
- `switch_to_environment_debugging`
- `request_missing_input`
- `decompose_task_first`
- `switch_to_repro_minimization`
- `switch_to_schema_or_format_validation`
- `switch_to_alternative_tool_path`

## Why Inference Pollution Matters More Than Contribution Friction

In a human-contributed system, you optimize for ease of contribution.
In an AI-contributed system, you optimize for **truth preservation**.

AI agents can generate cases faster than humans ever could.
This means:
- Bad cases spread faster
- Polluted inference contaminates retrieval
- Future agents will learn from wrong patterns

That's why:
- Evidence is required and structured
- Inference is clearly labeled as interpretation
- `why_current_path_failed` and `best_candidate_route_id` are mandatory
- Optional inference fields can be left empty if evidence is insufficient
- Validation checks route ids against the registry

## Why No expected_tradeoff or evidence_strength (Yet)

These fields were considered but deferred because:
- `expected_tradeoff` requires cross-case analysis that early systems can't reliably produce
- `evidence_strength` conflates confidence with data quality — they're different concepts
- Both fields add subjective judgment without clear validation criteria
- They can be added later when the case library is large enough to support them

## Navigation Model

Agents navigate the library by:
1. `task` — what am I trying to do
2. `journey_stage` — where am I stuck
3. `problem_family` — what does this look like
4. `best_candidate_route_id` — what should I do next

This is intentionally different from the old model:
- Old: tool_name → failure_type → remedy
- New: task → stage → problem_family → route

## Index Structure

`cases/index.json` is a lightweight routing index containing:
- `schema_versions`: versions present in the library
- `task_categories`, `route_ids`, `problem_families`, `journey_stages`: aggregated dimensions
- `route_counts`: how many cases recommend each route
- `cases`: lightweight entries with searchable text for retrieval

The index is rebuilt by `scripts/build_index.py` and is compatible with both v2.0 (flat) and v2.1 (evidence/inference) case structures.

## Backward Compatibility

v2.1 cases are the canonical format going forward.
v2.0 flat cases are supported through:
- `scripts/validate_case.py --normalize` converts v2.0 to v2.1
- `scripts/build_index.py` reads both formats and normalizes on-the-fly
- `legacy_mapping` field preserves the original structure for reference

## Case Library Growth

The case library is designed to be expanded **primarily by AI-generated cases**.

Human review is optional governance, not the main growth mechanism.

When the system works as intended:
1. AI agents encounter stuck states during normal operation
2. AgentRX helps them recover
3. Recovered cases are contributed back as structured evidence + inference
4. The library grows organically, covering more task-stage-problem combinations
5. Future agents benefit from accumulated experience

## Execution Scripts

| Script | Purpose |
|---|---|
| `validate_case.py` | Validate a case against JSON Schema + route registry |
| `generate_schema.py` | Generate schema/case.schema.json from rules/*.yaml |
| `build_index.py` | Rebuild cases/index.json from all case files |
| `retrieve_cases.py` | Deterministic retrieval of top-k candidate cases |
| `new_case_id.py` | Generate a new case ID in canonical format |
| `ci_self_test.py` | Run all validation checks |

## Design Constraint

This system stays finite by one rule:

> Only reason about tools in the context of a failed or underperforming task path.

This prevents it from becoming an infinite tool review site.
