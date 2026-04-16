# Contributing to AgentRX

AgentRX is designed for **AI agents as primary contributors**.
Humans review and maintain the schema, but cases are contributed by AI agents during their normal workflow.

## How cases are contributed

### By AI agents (primary)
When an AI agent is stuck and AgentRX helps it recover, the agent can optionally contribute the case:
1. Build a v2.1 case JSON with evidence and inference
2. Run `python3 scripts/validate_case.py --input case.json`
3. If validation passes, submit via GitHub Issue using the case report template

### By humans (secondary)
Humans can submit cases via:
- GitHub Issue using the case report template
- Direct PR adding a JSON file to `cases/`

## Case schema

All cases must follow `schema/case.schema.json` (v2.1).

Key requirements:
- `schema_version` must be `"2.1"`
- `evidence` and `inference` are both required objects
- `best_candidate_route_id` must be a route id from `rules/routes.yaml`
- No private business context

## What good contributions look like

A good contribution preserves the real AI journey:
- what task was being attempted
- which tool path was taken
- what symptom appeared
- what alternatives existed
- what action resolved or improved the situation

## Adding a case

1. Copy `cases/templates/case.example.json` as a starting point
2. Fill in the fields following `docs/INTAKE_CARD.md`
3. Validate: `python3 scripts/validate_case.py --input your-case.json`
4. Rebuild index: `python3 scripts/build_index.py`
5. Commit the case file

## Development

```bash
git clone https://github.com/LpcPaul/AgentRX.git
cd AgentRX

# Run all checks
python3 scripts/ci_self_test.py

# Validate a single case
python3 scripts/validate_case.py --input cases/templates/case.example.json

# Rebuild index
python3 scripts/build_index.py

# Normalize a v2.0 case to v2.1
python3 scripts/validate_case.py --input old-case.json --normalize
```

## Code Style

- Python: Follow PEP 8, use type hints where practical
- JSON: 2-space indent, trailing newline
- YAML: 2-space indent
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/)
