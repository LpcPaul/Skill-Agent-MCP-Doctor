# Cases — v2 structure

Cases are no longer organized primarily by skill.

They are organized for the question an agent actually has when it is stuck:

> “I am trying to do **this task**, I am stuck at **this stage**, and I think the issue looks like **this problem family**. What should I do next?”

## Design rule

A case is not just a failure log.

A case is a **navigation artifact** that helps another agent choose the next action.

## New organization principle

Cases should be indexed by:

1. `task_category`
2. `journey_stage`
3. `suspected_problem_family`
4. `tool_triggered`
5. `recommended_next_step`

## Why this changed

Legacy organization by `by-skill/` and `by-type/` made retrieval efficient only when the agent already knew:
- which skill was involved
- which failure label applied

Real stuck states rarely begin that cleanly.

## Minimal case anatomy

A strong case captures:

- task
- stage
- symptom
- current tool path
- alternatives considered
- next-step recommendation
- abstract outcome
- confidence
- source pattern

## Example task categories

- `browse-web`
- `read-files`
- `transform-documents`
- `create-presentation`
- `analyze-data`
- `code-editing`
- `workflow-automation`
- `communicate-and-publish`

See `rules/task_taxonomy.yaml`.

## Legacy migration

Legacy cases can still be useful, but they should be migrated into the v2 schema.

A rough migration approach:

- `skill_triggered` -> `tool_triggered`
- infer `tool_type = skill`
- infer `task_category` from the described user goal
- map old `failure_type` into `suspected_problem_family`
- rewrite remedy as `recommended_next_step`
- add `alternatives_considered` when known

## Index expectations

`cases/index.json` should become a lightweight routing index, not a dump of all fields.

It should help the agent find candidate cases by:
- task
- stage
- symptom
- current tool path
- recommendation type

## Template

See `cases/templates/case.example.json`.
