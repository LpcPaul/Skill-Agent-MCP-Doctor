#!/usr/bin/env python3
"""
AgentRX CI Self-Test

Validates:
1. YAML files parse correctly
2. schema/case.schema.json is valid
3. routes.yaml has valid route definitions
4. rules/*.yaml consistency with schema enums
5. Example case passes validation
6. Index can be rebuilt

Run: python3 scripts/ci_self_test.py
"""

import json
import sys
import yaml
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ERRORS = []
WARNINGS = []


def check(condition, message, level="error"):
    if not condition:
        if level == "error":
            ERRORS.append(message)
        else:
            WARNINGS.append(message)
        print(f"  {'❌' if level == 'error' else '⚠️'}  {message}")
    else:
        print(f"  ✅ {message}")


# ── 1. YAML parsing ────────────────────────────────────────────

print("\n1. YAML parsing")

yaml_files = list(REPO_ROOT.rglob("*.yml")) + list(REPO_ROOT.rglob("*.yaml"))
yaml_files = [f for f in yaml_files if ".git" not in str(f) and "node_modules" not in str(f)]

for yf in sorted(yaml_files):
    try:
        with open(yf) as f:
            yaml.safe_load(f)
        check(True, f"{yf.relative_to(REPO_ROOT)} — valid YAML")
    except yaml.YAMLError as e:
        check(False, f"{yf.relative_to(REPO_ROOT)} — YAML parse error: {e}")


# ── 2. JSON Schema ─────────────────────────────────────────────

print("\n2. JSON Schema")

schema_path = REPO_ROOT / "schema" / "case.schema.json"
schema = None
try:
    with open(schema_path) as f:
        schema = json.load(f)
    check(True, "case.schema.json — valid JSON")
    check(schema.get("title", "").endswith("v2.1"), "case.schema.json — title indicates v2.1")
    check("evidence" in schema.get("properties", {}), "schema has 'evidence' object")
    check("inference" in schema.get("properties", {}), "schema has 'inference' object")

    required = schema.get("required", [])
    check("schema_version" in required, "schema requires 'schema_version'")
    check("evidence" in required, "schema requires 'evidence'")
    check("inference" in required, "schema requires 'inference'")
except json.JSONDecodeError as e:
    check(False, f"case.schema.json — JSON parse error: {e}")


# ── 3. Route Registry ──────────────────────────────────────────

print("\n3. Route Registry")

routes_path = REPO_ROOT / "rules" / "routes.yaml"
try:
    with open(routes_path) as f:
        routes_data = yaml.safe_load(f)
    routes = routes_data.get("routes", {})
    check(len(routes) >= 5, f"routes.yaml has {len(routes)} routes (min 5)")

    for rid, rdef in routes.items():
        check("label" in rdef, f"route '{rid}' has label")
        check("description" in rdef, f"route '{rid}' has description")
        check("applies_when" in rdef, f"route '{rid}' has applies_when")

    # Check route ids match schema enum
    if schema:
        schema_routes = set(schema["properties"].get("inference", {}).get("properties", {}).get("best_candidate_route_id", {}).get("enum", []))
        yaml_routes = set(routes.keys())
        check(schema_routes == yaml_routes, f"schema route enum matches routes.yaml ({len(schema_routes)} == {len(yaml_routes)})")
except yaml.YAMLError as e:
    check(False, f"routes.yaml — YAML parse error: {e}")


# ── 4. Rules consistency ───────────────────────────────────────

print("\n4. Rules consistency")

rules_dir = REPO_ROOT / "rules"
if schema:
    # Journey stages
    schema_stages = set(schema["properties"].get("inference", {}).get("properties", {}).get("journey_stage", {}).get("enum", []))
    try:
        with open(rules_dir / "journey_stages.yaml") as f:
            rules_stages = set(yaml.safe_load(f).get("journey_stages", {}).keys())
        check(schema_stages == rules_stages, f"journey_stage enum consistent (schema={len(schema_stages)}, rules={len(rules_stages)})")
    except Exception as e:
        check(False, f"journey_stages.yaml comparison failed: {e}", level="warning")

    # Problem families
    schema_families = set(schema["properties"].get("inference", {}).get("properties", {}).get("problem_family", {}).get("enum", []))
    try:
        with open(rules_dir / "problem_families.yaml") as f:
            rules_families = set(yaml.safe_load(f).get("problem_families", {}).keys())
        check(schema_families == rules_families, f"problem_family enum consistent (schema={len(schema_families)}, rules={len(rules_families)})")
    except Exception as e:
        check(False, f"problem_families.yaml comparison failed: {e}", level="warning")


# ── 5. Example case validation ─────────────────────────────────

print("\n5. Example case validation")

example_path = REPO_ROOT / "cases" / "templates" / "case.example.json"
if example_path.exists():
    try:
        with open(example_path) as f:
            example = json.load(f)
        check(example.get("schema_version") == "2.1", f"example case schema_version is '2.1' (got: {example.get('schema_version')})")
        check("evidence" in example, "example has 'evidence' object")
        check("inference" in example, "example has 'inference' object")

        # Validate with validate_case.py
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "validate_case.py"), "--input", str(example_path)],
            capture_output=True, text=True
        )
        check(result.returncode == 0, f"validate_case.py passed: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"    stderr: {result.stderr.strip()}")
    except json.JSONDecodeError as e:
        check(False, f"case.example.json — JSON parse error: {e}")
else:
    check(False, "cases/templates/case.example.json — file not found")


# ── 6. Index rebuild ───────────────────────────────────────────

print("\n6. Index rebuild")

result = subprocess.run(
    [sys.executable, str(REPO_ROOT / "scripts" / "build_index.py")],
    capture_output=True, text=True
)
check(result.returncode == 0, f"build_index.py succeeded")
if result.returncode == 0:
    for line in result.stdout.strip().split("\n"):
        print(f"    {line}")

    # Verify index was created
    index_path = REPO_ROOT / "cases" / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                index = json.load(f)
            check(index.get("schema_version") == "2.1", "index schema_version is '2.1'")
            check("route_ids" in index, "index has 'route_ids'")
            check("route_counts" in index, "index has 'route_counts'")
            check("cases" in index, "index has 'cases'")
        except json.JSONDecodeError as e:
            check(False, f"index.json — JSON parse error: {e}")
if result.returncode != 0:
    print(f"    stderr: {result.stderr.strip()}")


# ── Summary ───────────────────────────────────────────────────

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
    print(f"✅ All checks passed")
    sys.exit(0)
