# Cases — v2.1 structure

Cases are organized for the question an AI agent has when it is stuck:

> "I am trying to do **this task**, I am stuck at **this stage**, and I think the issue looks like **this problem family**. What should I do next?"

## Two-layer structure

Every case has:

| Layer | Purpose | Mutability |
|---|---|---|
| **Evidence** | Observable facts from the stuck context | Immutable |
| **Inference** | AI-generated diagnosis and prescription | Re-computable |

## Design rule

A case is not a failure log. It is a **navigation artifact** that helps another agent choose its next action.

## Index

`cases/index.json` is a lightweight routing index rebuilt by `scripts/build_index.py`.

It contains:
- `task_categories` — unique tasks
- `route_ids` — unique recommended routes
- `route_counts` — how many cases recommend each route
- `problem_families` — unique problem families
- `journey_stages` — unique journey stages
- `cases` — lightweight entries with searchable text

## Adding cases

1. Create a JSON file following `schema/case.schema.json` (v2.1)
2. Place it in `cases/` or a subdirectory
3. Run `python3 scripts/build_index.py` to rebuild the index
4. Run `python3 scripts/validate_case.py --input your-case.json` to validate

See `cases/templates/case.example.json` for a canonical example.

## Schema versions

- **v2.1** (current): evidence/inference split, route registry, standardized route ids
- **v2.0** (legacy): flat structure, tool-first organization
- v2.0 cases are supported through normalization in `build_index.py` and `validate_case.py --normalize`

## Legacy migration

Use `python3 scripts/validate_case.py --input old-case.json --normalize` to convert v2.0 flat cases to v2.1 structure.

See `docs/MIGRATION_GUIDE.md` for details.
