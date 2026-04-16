#!/usr/bin/env python3
"""
AgentRX — Validate a case JSON file.

Two-layer validation:
1. JSON Schema validation (via jsonschema library)
2. Cross-file rule consistency (routes, journey stages, problem families, task taxonomy)

Usage:
    python3 scripts/validate_case.py --input path/to/case.json
    python3 scripts/validate_case.py --input path/to/case.json --normalize
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema is required. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "case.schema.json"
RULES_DIR = ROOT / "rules"

# Deprecated value -> new value mappings for problem families
DEPRECATED_FAMILY_MAP = {
    "environment": "environment_or_config",
    "configuration": "environment_or_config",
    "observability_gap": "recovery_gap",
    "better_alternative_exists": "capability_mismatch",
    "hook_vs_model_boundary": "not_a_tooling_problem",
    "unknown": "environment_or_config",
}


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rules() -> dict:
    rules = {}
    for filename in ["routes.yaml", "journey_stages.yaml", "problem_families.yaml", "task_taxonomy.yaml"]:
        path = RULES_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            rules[filename] = yaml.safe_load(f)
    return rules


def get_valid_route_ids(routes_data: dict) -> set:
    return set(routes_data.get("routes", {}).keys())


def get_deprecated_routes(routes_data: dict) -> dict:
    return routes_data.get("deprecated_routes", {})


def validate_schema(case_data: dict, schema: dict) -> list[str]:
    """Layer 1: JSON Schema validation."""
    errors = []
    try:
        jsonschema.validate(instance=case_data, schema=schema)
    except jsonschema.ValidationError as e:
        # Extract a clean error message
        path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "(root)"
        errors.append(f"Schema error at '{path}': {e.message}")
    return errors


def validate_cross_file(case_data: dict, rules: dict) -> tuple[list[str], list[str]]:
    """Layer 2: Cross-file rule consistency. Returns (errors, warnings)."""
    errors = []
    warnings = []

    inference = case_data.get("inference", {})
    evidence = case_data.get("evidence", {})

    # Validate route id
    route_id = inference.get("best_candidate_route_id")
    if route_id:
        valid_routes = get_valid_route_ids(rules["routes.yaml"])
        deprecated_routes = get_deprecated_routes(rules["routes.yaml"])

        if route_id in deprecated_routes:
            new_route = deprecated_routes[route_id]
            warnings.append(f"Deprecated route '{route_id}' used. Auto-mapped to '{new_route}'.")
        elif route_id not in valid_routes:
            errors.append(f"Invalid route id '{route_id}'. Must be one of: {', '.join(sorted(valid_routes))}")

    # Validate journey stage
    journey_stage = inference.get("journey_stage")
    if journey_stage:
        valid_stages = set(rules["journey_stages.yaml"].get("journey_stages", {}).keys())
        if journey_stage not in valid_stages:
            errors.append(f"Invalid journey_stage '{journey_stage}'. Must be one of: {', '.join(sorted(valid_stages))}")

    # Validate problem family (with deprecated mapping)
    problem_family = inference.get("problem_family")
    if problem_family:
        valid_families = set(rules["problem_families.yaml"].get("problem_families", {}).keys())
        if problem_family in DEPRECATED_FAMILY_MAP:
            new_family = DEPRECATED_FAMILY_MAP[problem_family]
            warnings.append(
                f"Deprecated problem_family '{problem_family}' used. "
                f"Auto-mapped to '{new_family}'."
            )
        elif problem_family not in valid_families:
            errors.append(
                f"Invalid problem_family '{problem_family}'. "
                f"Must be one of: {', '.join(sorted(valid_families))}"
            )

    # Validate task
    task = evidence.get("task")
    if task:
        valid_tasks = set(rules["task_taxonomy.yaml"].get("task_categories", {}).keys())
        if task not in valid_tasks:
            errors.append(f"Invalid task '{task}'. Must be one of: {', '.join(sorted(valid_tasks))}")

    return errors, warnings


def normalize_case(case_data: dict) -> dict:
    """Apply auto-mappings for deprecated values."""
    inference = case_data.get("inference", {})

    # Map deprecated problem families
    old_family = inference.get("problem_family")
    if old_family in DEPRECATED_FAMILY_MAP:
        case_data["inference"]["problem_family"] = DEPRECATED_FAMILY_MAP[old_family]

    # Map deprecated routes
    routes_data = {}
    routes_path = RULES_DIR / "routes.yaml"
    with open(routes_path, "r", encoding="utf-8") as f:
        routes_data = yaml.safe_load(f)

    deprecated_routes = routes_data.get("deprecated_routes", {})
    old_route = inference.get("best_candidate_route_id")
    if old_route in deprecated_routes:
        case_data["inference"]["best_candidate_route_id"] = deprecated_routes[old_route]

    return case_data


def validate_case(input_path: str, normalize: bool = False) -> int:
    case_path = Path(input_path)
    if not case_path.exists():
        print(f"ERROR: File not found: {case_path}", file=sys.stderr)
        return 1

    with open(case_path, "r", encoding="utf-8") as f:
        try:
            case_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
            return 1

    schema = load_schema()
    rules = load_rules()

    all_errors = []
    all_warnings = []

    # Layer 1: Schema validation
    schema_errors = validate_schema(case_data, schema)
    all_errors.extend(schema_errors)

    # Layer 2: Cross-file validation
    cross_errors, cross_warnings = validate_cross_file(case_data, rules)
    all_errors.extend(cross_errors)
    all_warnings.extend(cross_warnings)

    # Apply normalization if requested
    if normalize and (cross_warnings or cross_errors):
        case_data = normalize_case(case_data)
        with open(case_path, "w", encoding="utf-8") as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Case normalized: {case_path}")

        # Re-validate after normalization
        all_errors = []
        all_warnings = []
        schema_errors = validate_schema(case_data, schema)
        all_errors.extend(schema_errors)
        cross_errors, cross_warnings = validate_cross_file(case_data, rules)
        all_errors.extend(cross_errors)
        all_warnings.extend(cross_warnings)

    # Output results
    if all_warnings:
        for w in all_warnings:
            print(f"WARNING: {w}")

    if all_errors:
        for e in all_errors:
            print(f"ERROR: {e}")
        return 1

    if all_warnings and not all_errors:
        print("Validation passed with warnings (auto-mapped deprecated values).")
        return 0

    print("Validation passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate a case JSON file against schema and rules.")
    parser.add_argument("--input", required=True, help="Path to the case JSON file")
    parser.add_argument("--normalize", action="store_true", help="Auto-map deprecated values and write back")
    args = parser.parse_args()

    exit_code = validate_case(args.input, args.normalize)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
