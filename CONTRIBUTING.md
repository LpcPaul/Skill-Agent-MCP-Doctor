# Contributing to AgentRX

Thanks for contributing.

This project is no longer a skill-only failure log.  
It is a **task-first diagnosis and action library** for AI tool paths.

## What good contributions look like

A good contribution preserves the real AI journey:

1. What task was the agent trying to complete?
2. Which stage did it get stuck in?
3. What symptom appeared?
4. Which tool path was active?
5. What alternatives were available?
6. What next action helped?
7. What still remained unresolved?

If your contribution only says “Tool X is bad,” it is too weak.

## Priority contribution types

### 1. Real cases
The most valuable contribution is a real case in the new schema.

Use:
- automatic case generation through the skill
- manual issue submission
- direct PR with a JSON case

See:
- `schema/case.schema.json`
- `cases/templates/case.example.json`
- `docs/CASE_COLLECTION_PLAN.md`

### 2. Taxonomy improvements
Improve:
- `rules/task_taxonomy.yaml`
- `rules/journey_stages.yaml`
- `rules/problem_families.yaml`

Only add categories if they clearly improve navigation.

### 3. Architecture clarification
Improve:
- `docs/ARCHITECTURE.md`
- `docs/INTAKE_CARD.md`
- README / SKILL wording

This project depends on agents asking better internal questions before searching.

### 4. Deterministic privacy / validation
Improve redaction and validation scripts when the schema changes.
The v2 documentation redesign intentionally moves faster than the current implementation.  
PRs that bring the scripts into full v2 alignment are welcome.

## Current contribution standard

Every case should be:

- **task-first**
- **stage-aware**
- **tool-path aware**
- **privacy-safe**
- **actionable**

That means every accepted case should make it easier for another agent to decide:
- continue current path
- switch tools
- inspect environment
- move to hook/workflow
- reframe the task
- or conclude it is not a tooling issue

## Manual submission checklist

Before submitting, confirm:

- [ ] `task_category` is human-task language, not a tool name
- [ ] `journey_stage` is one of the canonical stages
- [ ] `observed_symptom` describes the surface symptom
- [ ] `suspected_problem_family` is a best-fit family, not a vague complaint
- [ ] `recommended_next_step` is concrete
- [ ] `alternatives_considered` is present when meaningful
- [ ] no private URLs, file paths, names, or business content appear
- [ ] the case would still be useful to another agent in a different company

## Development notes

This update changes the information architecture first.  
Some implementation files may still need follow-up work to fully enforce the new schema.

That is expected in this migration phase.

## Suggested pull request scopes

Good PR scopes:
- rewrite one doc set around the new architecture
- add one task category bundle
- migrate a small batch of legacy cases
- update schema + issue template together
- update redaction / validation to support new fields

Avoid giant mixed PRs that rewrite docs, code, and 100+ cases at once.

## Style

- Prefer direct, operational language.
- Optimize for agent readability, not marketing language.
- Use examples that explain the routing logic.
- Keep task/category names stable once introduced.

## Questions

If you are unsure where a contribution belongs, open an issue and describe:
- the task
- the stage
- the symptom
- the suspected problem family
- the candidate next action
