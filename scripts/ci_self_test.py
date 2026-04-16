#!/usr/bin/env python3
"""
AgentRX CI Self-Test

Validates:
1. YAML files are properly formatted and parseable
2. case.schema.json is valid JSON Schema
3. cases/templates/case.example.json matches the schema
4. rules/*.yaml files parse correctly

Run: python3 scripts/ci_self_test.py
"""

import json
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ERRORS = []
WARNINGS = []


def check(condition, message, level="error"):
    """Record a check result."""
    if not condition:
        if level == "error":
            ERRORS.append(message)
        else:
            WARNINGS.append(message)
        print(f"  {'❌' if level == 'error' else '⚠️'}  {message}")
    else:
        print(f"  ✅ {message}")


# ── 1. YAML files ──────────────────────────────────────────────

print("\n1. YAML parsing")

yaml_files = list(REPO_ROOT.rglob("*.yml")) + list(REPO_ROOT.rglob("*.yaml"))
# Exclude node_modules, .git, etc.
yaml_files = [f for f in yaml_files if ".git" not in str(f) and "node_modules" not in str(f)]

for yf in sorted(yaml_files):
    try:
        with open(yf) as f:
            data = yaml.safe_load(f)
        check(True, f"{yf.relative_to(REPO_ROOT)} — valid YAML")
    except yaml.YAMLError as e:
        check(False, f"{yf.relative_to(REPO_ROOT)} — YAML parse error: {e}")


# ── 2. JSON Schema ─────────────────────────────────────────────

print("\n2. JSON Schema")

schema_path = REPO_ROOT / "schema" / "case.schema.json"
try:
    with open(schema_path) as f:
        schema = json.load(f)
    check(True, "case.schema.json — valid JSON")
    check("properties" in schema, "case.schema.json — has 'properties'")
    check("required" in schema, "case.schema.json — has 'required'")

    # Check key v2 fields exist
    required_fields = schema.get("required", [])
    for field in ["task_category", "journey_stage", "suspected_problem_family",
                   "recommended_next_step", "desired_outcome"]:
        check(field in schema.get("properties", {}),
              f"schema has '{field}' property")

except json.JSONDecodeError as e:
    check(False, f"case.schema.json — JSON parse error: {e}")


# ── 3. Example case matches schema ─────────────────────────────

print("\n3. Example case validation")

example_path = REPO_ROOT / "cases" / "templates" / "case.example.json"
if example_path.exists():
    try:
        with open(example_path) as f:
            example = json.load(f)
        check(True, "case.example.json — valid JSON")

        # Check required fields
        if "properties" in schema:
            for field in schema.get("required", []):
                check(field in example, f"example has required field '{field}'")

        # Check no unknown fields (additionalProperties: false)
        if schema.get("additionalProperties") == False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(example.keys()) - allowed
            check(len(extra) == 0, f"example has no extra fields (found: {extra})")
    except json.JSONDecodeError as e:
        check(False, f"case.example.json — JSON parse error: {e}")
else:
    check(False, "cases/templates/case.example.json — file not found")


# ── 4. Rules files ─────────────────────────────────────────────

print("\n4. Rules validation")

rules_dir = REPO_ROOT / "rules"
expected_rules = ["task_taxonomy.yaml", "journey_stages.yaml",
                  "problem_families.yaml", "failure_types.yaml"]

for rule_file in expected_rules:
    rp = rules_dir / rule_file
    if rp.exists():
        try:
            with open(rp) as f:
                data = yaml.safe_load(f)
            check(True, f"rules/{rule_file} — valid YAML")
            check(isinstance(data, dict) and len(data) > 0,
                  f"rules/{rule_file} — has content")
        except yaml.YAMLError as e:
            check(False, f"rules/{rule_file} — YAML parse error: {e}")
    else:
        check(False, f"rules/{rule_file} — file not found")


# ── 5. Cross-file consistency ──────────────────────────────────

print("\n5. Cross-file consistency")

# journey_stages in schema vs rules
if "properties" in schema and rules_dir.exists():
    schema_stages = set(schema["properties"].get("journey_stage", {}).get("enum", []))
    try:
        with open(rules_dir / "journey_stages.yaml") as f:
            data = yaml.safe_load(f)
            rules_stages = set(data.get("journey_stages", {}).keys())
        check(schema_stages == rules_stages,
              f"journey_stage enum matches journey_stages.yaml "
              f"(schema={len(schema_stages)}, rules={len(rules_stages)})")
    except Exception as e:
        check(False, f"journey_stages.yaml comparison failed: {e}", level="warning")

    schema_families = set(schema["properties"].get("suspected_problem_family", {}).get("enum", []))
    try:
        with open(rules_dir / "problem_families.yaml") as f:
            data = yaml.safe_load(f)
            rules_families = set(data.get("problem_families", {}).keys())
        check(schema_families == rules_families,
              f"suspected_problem_family enum matches problem_families.yaml "
              f"(schema={len(schema_families)}, rules={len(rules_families)})")
    except Exception as e:
        check(False, f"problem_families.yaml comparison failed: {e}", level="warning")


# ── Summary ────────────────────────────────────────────────────

print("\n" + "=" * 50)
if ERRORS:
    print(f"❌ {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
    for e in ERRORS:
        print(f"   ERROR: {e}")
    sys.exit(1)
elif WARNINGS:
    print(f"✅ All checks passed ({len(WARNINGS)} warning(s))")
    for w in WARNINGS:
        print(f"   WARNING: {w}")
    sys.exit(0)
else:
    print(f"✅ All {sum(1 for _ in yaml_files) + 10} checks passed")
    sys.exit(0)
