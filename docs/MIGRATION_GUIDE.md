# Migration Guide — from Skill Doctor v1 to AgentRX v2.1

## What changed

### v1 center of gravity
- skill
- failure_type
- by-skill cases
- by-type cases

### v2.0 center of gravity
- task_category
- journey_stage
- suspected_problem_family
- recommended_next_step
- multi-tool path comparisons

### v2.1 center of gravity
- **evidence / inference split** — facts vs. interpretation
- **route registry** — standardized action paths, not tool names
- **why_current_path_failed** — core attribution field
- **best_candidate_route_id** — core prescription field
- **schema_version** — explicit version tracking

## Recommended migration order

### Step 1 — update docs first
Replace:
- README
- SKILL.md
- CONTRIBUTING
- hooks/README
- issue template
- schema docs
- case collection docs

### Step 2 — freeze legacy case additions
Do not keep adding new v1-style cases while the architecture is changing.

### Step 3 — add v2 schema and index
Introduce:
- `schema/case.schema.json`
- `rules/problem_families.yaml`
- `rules/task_taxonomy.yaml`
- `rules/journey_stages.yaml`
- `cases/templates/case.example.json`

### Step 4 — map legacy fields
Use this rough mapping:

- `skill_triggered` -> `tool_triggered`
- `failure_type` -> `suspected_problem_family`
- `remedy` -> `recommendation_detail`
- `remedy_type` -> `recommended_next_step`
- `other_active_skills` -> `other_tools_in_path` with `type=skill`

### Step 5 — re-index old cases
For each legacy case:
1. infer the task
2. infer the stage
3. infer the symptom
4. infer the problem family
5. infer the next action

### Step 6 — update validation / redaction
Bring scripts into full v2 compatibility.

## Important warning

Do not migrate literally field-by-field without reframing the case.

The point of migration is not merely schema translation.
The point is to preserve the **navigation value** of the case.

## Good migration question

Ask:
> If another agent were stuck in a similar situation, would this migrated case help it choose a better next action?

If not, the migration is too shallow.

---

## v2.0 → v2.1 Migration

If you have v2.0 flat cases, convert them to v2.1 evidence/inference structure:

### Automatic conversion

```bash
python3 scripts/validate_case.py --input old-case.json --normalize
```

This converts:
- `task_category` → `evidence.task`
- `task_goal` → `evidence.desired_outcome`
- `tool_triggered` + `tool_type` → `evidence.attempted_path`
- `observed_symptom` → `evidence.symptom`
- `journey_stage` → `inference.journey_stage`
- `suspected_problem_family` → `inference.problem_family`
- `diagnosis_summary` → `inference.why_current_path_failed`
- `recommended_next_step` → `inference.best_candidate_route_id` (with mapping)
- `recommendation_detail` → `inference.best_candidate_route_detail`
- `outcome` → `resolution.outcome`
- `confidence` → `inference.confidence`
- All original values preserved in `legacy_mapping`

### Route id mapping

| v2.0 `recommended_next_step` | v2.1 `best_candidate_route_id` |
|---|---|
| `switch_tool_within_same_task` | `switch_to_alternative_tool_path` |
| `adjust_current_tool_invocation` | `switch_to_alternative_tool_path` |
| `inspect_environment_or_permissions` | `switch_to_environment_debugging` |
| `move_to_hook_or_workflow` | `decompose_task_first` |
| `reframe_task_before_retry` | `request_missing_input` |
| `ask_for_one_missing_constraint` | `request_missing_input` |
| `stop_tooling_changes_not_a_tool_issue` | `request_missing_input` |
| `other` | `switch_to_alternative_tool_path` |

### Manual review after auto-conversion

After running `--normalize`, review:
1. `evidence.task` — is it a human task, not a tool name?
2. `evidence.symptom` — is it an observation, not a diagnosis?
3. `inference.why_current_path_failed` — does it explain the mismatch?
4. `inference.best_candidate_route_id` — is it a route id, not a tool name?
5. `inference.best_candidate_route_detail` — add context if the auto-mapped detail is too generic

### Index compatibility

`scripts/build_index.py` reads both v2.0 and v2.1 cases and normalizes them on-the-fly.
No manual pre-processing is needed for index building.
