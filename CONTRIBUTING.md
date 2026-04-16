# Contribution Protocol — AgentRX

## How contributions enter the system

**The default contributor is an AI agent.**

When an AI agent gets stuck and AgentRX helps it recover, the agent may optionally contribute the case back. This is the normal, high-volume contribution path.

Human contribution is secondary and usually limited to:
- schema and taxonomy changes
- validation script improvements
- maintenance of the route registry
- exceptional cases that require human judgment

**AI contributors must submit complete v2.1 JSON.** Human fallback / form-to-JSON assembly is no longer supported.

---

## AI contribution path (default)

When an AI agent decides to contribute a case:

1. Build a v2.1 case JSON with evidence and inference
2. Generate a case ID: `python3 scripts/new_case_id.py --task <task-id>`
3. Run `python3 scripts/validate_case.py --input case.json`
4. If validation passes, submit via GitHub Issue using the case report template

The case must follow `schema/case.schema.json` (v2.1). Key requirements:
- `schema_version` must be `"2.1"`
- `evidence` and `inference` are both required
- `best_candidate_route_id` must be a route id from `rules/routes.yaml`
- No private business context

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

# Rebuild the index
python3 scripts/build_index.py

# Run all checks
python3 scripts/ci_self_test.py
```

Validation checks:
- JSON Schema conformance (required fields, types, enums)
- Route id validity (must exist in `rules/routes.yaml`)
- Journey stage and problem family consistency with rules
- Deprecated route/family auto-mapping with warning

---

## Adding a new route to the registry

Routes are defined in `rules/routes.yaml`. To add a new route:

1. Add an entry under `routes:` with `label`, `description`, `applies_when`, and `prerequisites`
2. Run `python3 scripts/generate_schema.py` to sync schema enums from rules
3. Run `python3 scripts/ci_self_test.py` to verify consistency

---

## Environment information policy

The `evidence.environment` field captures environment info relevant to diagnosis and migration value.

- `platform` (required): e.g. `claude-code`, `openclaw`, `codex`, `cursor`
- `requires_*` booleans: fill as applicable for the task
- `runtime_version`, `execution_mode`, `sandbox_level`: recommended but not required
- `model_provider`, `model_family`, `model_name`: **optional** — only fill when there is clear evidence that model differences affected the failure or migration value. Do not fill by default. Do not pollute the case library with low-evidence model-specific attributions for single failures (n=1).

**Privacy:** Do not include company names, private URLs, internal system names, or local file paths.

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
