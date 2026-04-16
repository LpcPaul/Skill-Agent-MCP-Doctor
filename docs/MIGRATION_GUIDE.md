# Migration Guide — from Skill Doctor v1 to AgentRX v2

## What changed

### v1 center of gravity
- skill
- failure_type
- by-skill cases
- by-type cases

### v2 center of gravity
- task_category
- journey_stage
- suspected_problem_family
- recommended_next_step
- multi-tool path comparisons

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
