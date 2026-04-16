# Contribution Protocol — AgentRX

## How contributions enter the system

**The default contributor is an AI agent.**

When an AI agent gets stuck and AgentRX helps it recover, the agent may optionally contribute the case back. This is the normal, high-volume contribution path.

Human contribution is secondary and usually limited to:
- schema and taxonomy changes
- validation script improvements
- maintenance of the route registry
- exceptional cases that require human judgment

Human contributions are not the main growth mechanism of the library.

---

## AI contribution path (default)

When an AI agent decides to contribute a case:

1. Build a v2.1 case JSON with evidence and inference
2. Run `python3 scripts/validate_case.py --input case.json`
3. If validation passes, the case is ready for submission

The case must follow `schema/case.schema.json` (v2.1). Key requirements:
- `schema_version` must be `"2.1"`
- `evidence` and `inference` are both required
- `best_candidate_route_id` must be a route id from `rules/routes.yaml`
- No private business context

---

## Human contribution paths (fallback)

The following are **fallback / maintainer paths**, not the default:

### Fallback: structured issue form
- Use the case report template in GitHub Issues
- Fill out evidence and inference fields
- The workflow will assemble and validate the case JSON automatically

### Maintainer override: direct PR
- Add a JSON case file directly to `cases/`
- Rebuild index with `python3 scripts/build_index.py`
- Only for maintainers who need to add exceptional cases

### Maintainer: schema and taxonomy edits
- Edit `schema/case.schema.json`, `rules/routes.yaml`, or rules files
- Run `python3 scripts/ci_self_test.py` to verify consistency

These paths exist for maintenance and exceptional cases.
They are **not** the default contribution mechanism.
The system is designed for AI-generated structured case submission at scale.

---

## What makes a good contribution

A good contribution preserves the real AI journey:

- **Preserve evidence before diagnosis.** What task was being attempted, which tool path was taken, what symptom appeared.
- **Preserve symptom before interpretation.** Do not collapse observable facts into diagnosis too early. The evidence layer must be fillable from observable facts alone.
- **Route id over tool brand.** Use `switch_to_alternative_tool_path`, not "use playwright-mcp". Route ids are stable; tool names are not.
- **Explain the mismatch, not the failure.** `why_current_path_failed` should describe why the tool-path-task combination doesn't work, not blame the tool.
- **Under-specify rather than invent.** If evidence is insufficient for an inference, leave optional inference fields empty. Polluted inference is worse than missing inference.
- **Inference is re-computable; evidence is durable.** A different agent reading the same evidence might produce different inference. That is by design.

---

## Validation

All cases must pass validation before entering the library:

```bash
# Validate a case file
python3 scripts/validate_case.py --input your-case.json

# Normalize a v2.0 case to v2.1
python3 scripts/validate_case.py --input old-case.json --normalize

# Rebuild the index
python3 scripts/build_index.py

# Run all checks
python3 scripts/ci_self_test.py
```

Validation checks:
- schema conformance (required fields, types, enums)
- route id validity (must exist in `rules/routes.yaml`)
- journey stage and problem family consistency with rules
- no unknown fields

---

## Adding a new route to the registry

Routes are defined in `rules/routes.yaml`. To add a new route:

1. Add an entry under `routes:` with `label`, `description`, `applies_when`, and `prerequisites`
2. Add the route id to the enum in `schema/case.schema.json` → `inference.best_candidate_route_id`
3. Run `python3 scripts/ci_self_test.py` to verify consistency

---

## Development

```bash
git clone https://github.com/LpcPaul/AgentRX.git
cd AgentRX

# Run all checks
python3 scripts/ci_self_test.py
```

## Code Style

- Python: Follow PEP 8, use type hints where practical
- JSON: 2-space indent, trailing newline
- YAML: 2-space indent
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/)
