#!/usr/bin/env python3
"""
AgentRX — Case Validation Script

Validates a case JSON file against:
1. schema/case.schema.json (JSON Schema)
2. rules/routes.yaml (route id must exist)
3. rules/journey_stages.yaml (journey stage must exist)
4. rules/problem_families.yaml (problem family must exist)

Usage:
    python3 scripts/validate_case.py --input /path/to/case.json
    python3 scripts/validate_case.py --input /path/to/case.json --strict

Exit codes:
    0 — valid
    1 — validation errors found
    2 — schema or config file missing
    3 — input file not found or not valid JSON
"""

import argparse
import json
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "case.schema.json"
ROUTES_PATH = REPO_ROOT / "rules" / "routes.yaml"
STAGES_PATH = REPO_ROOT / "rules" / "journey_stages.yaml"
FAMILIES_PATH = REPO_ROOT / "rules" / "problem_families.yaml"


def load_yaml(path: Path):
    """Load a YAML file, return dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_json(path: Path):
    """Load a JSON file, return dict."""
    with open(path) as f:
        return json.load(f)


def validate_schema(case: dict, schema: dict) -> list[str]:
    """Basic JSON Schema validation (required fields, types, enums)."""
    errors = []

    # Check required fields
    for field in schema.get("required", []):
        if field not in case:
            errors.append(f"Missing required field: {field}")

    props = schema.get("properties", {})

    # Validate top-level properties
    for field, value in case.items():
        if field not in props:
            if schema.get("additionalProperties") == False:
                errors.append(f"Unknown field: {field}")
            continue

        prop_def = props[field]

        # Type check
        expected_type = prop_def.get("type")
        if expected_type == "object" and not isinstance(value, dict):
            errors.append(f"Field '{field}' must be an object, got {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            errors.append(f"Field '{field}' must be an array, got {type(value).__name__}")
        elif expected_type == "string" and not isinstance(value, str):
            errors.append(f"Field '{field}' must be a string, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"Field '{field}' must be a boolean, got {type(value).__name__}")

        # Enum check
        if "enum" in prop_def and isinstance(value, str):
            if value not in prop_def["enum"]:
                errors.append(f"Field '{field}' value '{value}' not in allowed values: {prop_def['enum']}")

        # Const check
        if "const" in prop_def and value != prop_def["const"]:
            errors.append(f"Field '{field}' must be '{prop_def['const']}', got '{value}'")

        # Max length check
        if "maxLength" in prop_def and isinstance(value, str):
            if len(value) > prop_def["maxLength"]:
                errors.append(f"Field '{field}' exceeds maxLength {prop_def['maxLength']} (length: {len(value)})")

        # Pattern check
        if "pattern" in prop_def and isinstance(value, str):
            import re
            if not re.match(prop_def["pattern"], value):
                errors.append(f"Field '{field}' does not match pattern: {prop_def['pattern']}")

        # Nested object validation
        if expected_type == "object" and isinstance(value, dict) and "properties" in prop_def:
            nested_props = prop_def["properties"]
            for nf, nv in value.items():
                if nf not in nested_props:
                    if prop_def.get("additionalProperties") == False:
                        errors.append(f"Field '{field}' has unknown sub-field: {nf}")
                    continue
                nprop = nested_props[nf]
                if "enum" in nprop and isinstance(nv, str) and nv not in nprop["enum"]:
                    errors.append(f"Field '{field}.{nf}' value '{nv}' not in allowed values")

        # Array item validation
        if expected_type == "array" and isinstance(value, list) and "items" in prop_def:
            item_def = prop_def["items"]
            if "maxLength" in item_def:
                for i, item in enumerate(value):
                    if isinstance(item, str) and len(item) > item_def["maxLength"]:
                        errors.append(f"Field '{field}[{i}]' exceeds maxLength {item_def['maxLength']}")
            if "maxItems" in prop_def and len(value) > prop_def["maxItems"]:
                errors.append(f"Field '{field}' has {len(value)} items, max is {prop_def['maxItems']}")
            # Nested object items
            if item_def.get("type") == "object" and "properties" in item_def:
                item_props = item_def["properties"]
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        for ik, iv in item.items():
                            if ik in item_props and "enum" in item_props[ik]:
                                if isinstance(iv, str) and iv not in item_props[ik]["enum"]:
                                    errors.append(f"Field '{field}[{i}].{ik}' value '{iv}' not in allowed values")

    # Validate nested evidence object
    if "evidence" in case and isinstance(case["evidence"], dict):
        evidence = case["evidence"]
        evidence_def = props.get("evidence", {})
        e_props = evidence_def.get("properties", {})

        for ef in evidence_def.get("required", []):
            if ef not in evidence:
                errors.append(f"Missing required evidence field: {ef}")

        if "attempted_path" in evidence and isinstance(evidence["attempted_path"], dict):
            ap = evidence["attempted_path"]
            ap_def = e_props.get("attempted_path", {})
            for apf in ap_def.get("required", []):
                if apf not in ap:
                    errors.append(f"Missing required attempted_path field: {apf}")

    # Validate nested inference object
    if "inference" in case and isinstance(case["inference"], dict):
        inference = case["inference"]
        inference_def = props.get("inference", {})

        for inf in inference_def.get("required", []):
            if inf not in inference:
                errors.append(f"Missing required inference field: {inf}")

        # Check best_candidate_route_id is valid (will be validated against routes.yaml below)
        if "best_candidate_route_id" in inference:
            route_id = inference["best_candidate_route_id"]
            if isinstance(route_id, str) and route_id not in get_valid_route_ids():
                errors.append(f"Invalid route id: {route_id}")

    return errors


def get_valid_route_ids() -> set[str]:
    """Load route ids from routes.yaml."""
    try:
        data = load_yaml(ROUTES_PATH)
        routes = data.get("routes", {})
        return set(routes.keys())
    except Exception:
        return set()


def get_valid_stages() -> set[str]:
    """Load journey stages from journey_stages.yaml."""
    try:
        data = load_yaml(STAGES_PATH)
        return set(data.get("journey_stages", {}).keys())
    except Exception:
        return set()


def get_valid_families() -> set[str]:
    """Load problem families from problem_families.yaml."""
    try:
        data = load_yaml(FAMILIES_PATH)
        return set(data.get("problem_families", {}).keys())
    except Exception:
        return set()


def validate_cross_refs(case: dict) -> list[str]:
    """Validate cross-file references."""
    errors = []
    inference = case.get("inference", {})

    # Journey stage must exist in rules
    stage = inference.get("journey_stage")
    if stage and stage not in get_valid_stages():
        errors.append(f"journey_stage '{stage}' not found in rules/journey_stages.yaml")

    # Problem family must exist in rules
    family = inference.get("problem_family")
    if family and family not in get_valid_families():
        errors.append(f"problem_family '{family}' not found in rules/problem_families.yaml")

    # Route id must exist in routes.yaml
    route_id = inference.get("best_candidate_route_id")
    if route_id and route_id not in get_valid_route_ids():
        errors.append(f"best_candidate_route_id '{route_id}' not found in rules/routes.yaml")

    return errors


def normalize_v2_to_v21(case: dict) -> dict:
    """
    Convert a v2.0 flat case to v2.1 evidence/inference structure.
    This is a best-effort normalization, not a perfect migration.
    """
    if case.get("schema_version") == "2.1":
        return case

    # Check if it looks like a v2.0 flat case
    if "task_category" in case and "evidence" not in case:
        normalized = {
            "schema_version": "2.1",
            "id": case.get("case_id", case.get("id", "unknown")),
            "title": case.get("title", f"{case.get('task_category', 'unknown')} {case.get('journey_stage', 'unknown')} {case.get('suspected_problem_family', 'unknown')}"),
            "summary": case.get("diagnosis_summary", case.get("recommendation_detail", "")),
            "created_at": case.get("timestamp", case.get("created_at", "")),
            "tags": case.get("tags", []),
            "evidence": {
                "task": case.get("task_category", ""),
                "desired_outcome": case.get("task_goal", case.get("desired_outcome", "")),
                "attempted_path": {
                    "tool": case.get("tool_triggered", ""),
                    "tool_type": case.get("tool_type", "unknown"),
                    "other_tools": case.get("other_tools_in_path", [])
                },
                "symptom": case.get("observed_symptom", ""),
                "symptom_tags": case.get("symptom_tags", []),
                "context": "",
                "environment": case.get("environment", case.get("constraints", {})),
                "failed_step": "",
                "artifacts_used": [],
                "reproduction_steps": case.get("attempted_actions", [])
            },
            "inference": {
                "journey_stage": case.get("journey_stage", "unknown"),
                "problem_family": case.get("suspected_problem_family", "unknown"),
                "why_current_path_failed": case.get("diagnosis_summary", ""),
                "best_candidate_route_id": map_next_step_to_route(case.get("recommended_next_step", "")),
                "best_candidate_route_detail": case.get("recommendation_detail", ""),
                "prerequisites_for_switch": [],
                "confidence": case.get("confidence", "medium")
            },
            "resolution": {
                "outcome": case.get("outcome", "unknown"),
                "follow_up_notes": ""
            },
            "verified": case.get("verified", False),
            "related_cases": case.get("related_cases", []),
            "legacy_mapping": {
                "legacy_schema_version": case.get("schema_version", "2.0"),
                "legacy_failure_type": case.get("legacy_mapping", {}).get("legacy_failure_type", ""),
                "legacy_skill_triggered": case.get("legacy_mapping", {}).get("legacy_skill_triggered", ""),
                "legacy_task_category": case.get("task_category", ""),
                "legacy_journey_stage": case.get("journey_stage", "")
            }
        }
        return normalized

    return case


def map_next_step_to_route(next_step: str) -> str:
    """Map v2.0 recommended_next_step to v2.1 route id."""
    mapping = {
        "switch_tool_within_same_task": "switch_to_alternative_tool_path",
        "adjust_current_tool_invocation": "switch_to_alternative_tool_path",
        "inspect_environment_or_permissions": "switch_to_environment_debugging",
        "move_to_hook_or_workflow": "decompose_task_first",
        "reframe_task_before_retry": "request_missing_input",
        "ask_for_one_missing_constraint": "request_missing_input",
        "stop_tooling_changes_not_a_tool_issue": "request_missing_input",
        "other": "switch_to_alternative_tool_path"
    }
    return mapping.get(next_step, "switch_to_alternative_tool_path")


def main():
    parser = argparse.ArgumentParser(description="Validate an AgentRX case file")
    parser.add_argument("--input", required=True, help="Path to case JSON file")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    parser.add_argument("--normalize", action="store_true", help="Normalize v2.0 to v2.1 and write back")
    args = parser.parse_args()

    input_path = Path(args.input)

    # Check files exist
    for path in [SCHEMA_PATH, ROUTES_PATH, STAGES_PATH, FAMILIES_PATH]:
        if not path.exists():
            print(f"ERROR: Required file missing: {path}", file=sys.stderr)
            sys.exit(2)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(3)

    try:
        with open(input_path) as f:
            case = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(3)

    # Normalize if requested
    if args.normalize:
        case = normalize_v2_to_v21(case)
        with open(input_path, "w") as f:
            json.dump(case, f, indent=2)
        print(f"Normalized {input_path} to v2.1")

    schema = load_json(SCHEMA_PATH)

    # Run validation
    errors = []
    errors.extend(validate_schema(case, schema))
    errors.extend(validate_cross_refs(case))

    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"PASSED: {input_path.name} is valid (schema_version: {case.get('schema_version', 'unknown')})")
        sys.exit(0)


if __name__ == "__main__":
    main()
