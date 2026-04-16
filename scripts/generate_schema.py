#!/usr/bin/env python3
"""
AgentRX — Generate schema/case.schema.json from rules/*.yaml

This script reads the canonical rule files and regenerates the JSON Schema
enums so that rules/*.yaml are the single source of truth.

Usage:
    python3 scripts/generate_schema.py
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
SCHEMA_PATH = ROOT / "schema" / "case.schema.json"


def load_yaml(filename: str) -> dict:
    path = RULES_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_route_ids(routes_data: dict) -> list[str]:
    return list(routes_data.get("routes", {}).keys())


def get_journey_stages(journey_data: dict) -> list[str]:
    return list(journey_data.get("journey_stages", {}).keys())


def get_problem_families(families_data: dict) -> list[str]:
    return list(families_data.get("problem_families", {}).keys())


def get_task_ids(task_data: dict) -> list[str]:
    return list(task_data.get("task_categories", {}).keys())


def generate_schema() -> dict:
    routes_data = load_yaml("routes.yaml")
    journey_data = load_yaml("journey_stages.yaml")
    families_data = load_yaml("problem_families.yaml")
    task_data = load_yaml("task_taxonomy.yaml")

    route_ids = get_route_ids(routes_data)
    journey_stages = get_journey_stages(journey_data)
    problem_families = get_problem_families(families_data)
    task_ids = get_task_ids(task_data)

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AgentRX Case Report — v2.1",
        "description": "AI-only case schema with evidence / inference separation. Every case represents one stuck-state diagnosis contributed by an AI agent.",
        "type": "object",
        "required": [
            "schema_version",
            "id",
            "title",
            "summary",
            "created_at",
            "tags",
            "evidence",
            "inference"
        ],
        "properties": {
            "schema_version": {
                "type": "string",
                "const": "2.1",
                "description": "Schema version. Must be '2.1'."
            },
            "id": {
                "type": "string",
                "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{6,40}$",
                "description": "Unique case ID. Example: 2026-04-16-browse-web-a13f92cd"
            },
            "title": {
                "type": "string",
                "maxLength": 120,
                "description": "Short human-readable title. Example: browse-web execute-task capability_mismatch."
            },
            "summary": {
                "type": "string",
                "maxLength": 300,
                "description": "One-sentence summary of the stuck state and resolution."
            },
            "created_at": {
                "type": "string",
                "format": "date-time"
            },
            "updated_at": {
                "type": "string",
                "format": "date-time"
            },
            "source": {
                "type": "string",
                "maxLength": 120,
                "description": "Abstract source tag. No private URLs or usernames. For synthetic seeds, use 'synthetic-seed'."
            },
            "verified": {
                "type": "boolean",
                "default": False
            },
            "tags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": 40
                },
                "maxItems": 12,
                "description": "Searchable tags derived from task, stage, and problem family."
            },
            "evidence": {
                "type": "object",
                "description": "Facts extracted directly from the stuck context. These are immutable observations, not diagnoses.",
                "required": [
                    "task",
                    "desired_outcome",
                    "attempted_path",
                    "symptom"
                ],
                "properties": {
                    "task": {
                        "type": "string",
                        "enum": task_ids,
                        "description": "What job was being attempted. Must be a canonical task ID from rules/task_taxonomy.yaml."
                    },
                    "desired_outcome": {
                        "type": "string",
                        "maxLength": 200,
                        "description": "What the agent was trying to accomplish next."
                    },
                    "attempted_path": {
                        "type": "object",
                        "required": ["tool", "tool_type"],
                        "properties": {
                            "tool": {
                                "type": "string",
                                "maxLength": 100,
                                "description": "Name of the tool or path segment that was used."
                            },
                            "tool_type": {
                                "type": "string",
                                "enum": [
                                    "skill", "mcp", "plugin", "builtin",
                                    "agent", "workflow", "hook", "unknown"
                                ]
                            },
                            "other_tools": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "type"],
                                    "properties": {
                                        "name": {"type": "string", "maxLength": 100},
                                        "type": {
                                            "type": "string",
                                            "enum": ["skill", "mcp", "plugin", "builtin", "agent", "workflow", "hook", "unknown"]
                                        },
                                        "role": {"type": "string", "maxLength": 80}
                                    },
                                    "additionalProperties": False
                                },
                                "maxItems": 20
                            }
                        },
                        "additionalProperties": False
                    },
                    "symptom": {
                        "type": "string",
                        "maxLength": 300,
                        "description": "Surface-level observation. No diagnosis language."
                    },
                    "symptom_tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 50},
                        "maxItems": 12
                    },
                    "context": {
                        "type": "string",
                        "maxLength": 400,
                        "description": "Additional context that explains the situation without being business-specific."
                    },
                    "environment": {
                        "type": "object",
                        "required": ["platform"],
                        "properties": {
                            "platform": {
                                "type": "string",
                                "enum": ["claude-code", "claude-ai", "openclaw", "codex", "cursor", "gemini-cli", "other"]
                            },
                            "runtime_version": {"type": "string", "maxLength": 40},
                            "execution_mode": {"type": "string", "enum": ["local", "cloud", "hybrid"]},
                            "sandbox_level": {"type": "string", "enum": ["strict", "partial", "none"]},
                            "model_provider": {"type": "string", "maxLength": 60},
                            "model_family": {"type": "string", "maxLength": 60},
                            "model_name": {"type": "string", "maxLength": 80},
                            "requires_login": {"type": "boolean"},
                            "requires_dynamic_render": {"type": "boolean"},
                            "requires_local_filesystem": {"type": "boolean"},
                            "requires_network": {"type": "boolean"},
                            "requires_deterministic_execution": {"type": "boolean"},
                            "notes": {"type": "string", "maxLength": 300}
                        },
                        "additionalProperties": False
                    },
                    "failed_step": {
                        "type": "string",
                        "maxLength": 200,
                        "description": "The specific step in the tool path that failed or underperformed."
                    },
                    "artifacts_used": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 120},
                        "maxItems": 20,
                        "description": "Abstract file types or resource types used. No private file paths."
                    },
                    "reproduction_steps": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 180},
                        "maxItems": 20,
                        "description": "What was already tried. Prevents looped retries."
                    }
                },
                "additionalProperties": False
            },
            "inference": {
                "type": "object",
                "description": "AI-generated diagnosis and prescription based on the evidence layer.",
                "required": [
                    "journey_stage",
                    "problem_family",
                    "why_current_path_failed",
                    "best_candidate_route_id"
                ],
                "properties": {
                    "journey_stage": {
                        "type": "string",
                        "enum": journey_stages
                    },
                    "problem_family": {
                        "type": "string",
                        "enum": problem_families
                    },
                    "why_current_path_failed": {
                        "type": "string",
                        "maxLength": 300,
                        "description": "Short explanation of why the current path is unsuitable for continued progress."
                    },
                    "best_candidate_route_id": {
                        "type": "string",
                        "enum": route_ids,
                        "description": "Standard route id from rules/routes.yaml. Must NOT be a free-text tool brand name."
                    },
                    "best_candidate_route_detail": {
                        "type": "string",
                        "maxLength": 400,
                        "description": "Optional explanation of why this route is recommended."
                    },
                    "prerequisites_for_switch": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 60},
                        "maxItems": 10,
                        "description": "Lightweight checklist of what must be true before switching."
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence in this inference."
                    }
                },
                "additionalProperties": False
            },
            "resolution": {
                "type": "object",
                "description": "What happened after the recommendation was applied.",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "enum": ["resolved", "partially_resolved", "unresolved", "unknown"]
                    },
                    "follow_up_notes": {
                        "type": "string",
                        "maxLength": 300
                    }
                },
                "additionalProperties": False
            },
            "related_cases": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 20
            },
            "legacy_mapping": {
                "type": "object",
                "description": "Preserves mapping from v1/v2.0 fields for backward compatibility.",
                "properties": {
                    "legacy_schema_version": {"type": "string"},
                    "legacy_failure_type": {"type": "string"},
                    "legacy_skill_triggered": {"type": "string"},
                    "legacy_task_category": {"type": "string"},
                    "legacy_journey_stage": {"type": "string"}
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    return schema


def main():
    print("Generating schema from rules/*.yaml ...")
    schema = generate_schema()

    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Schema written to: {SCHEMA_PATH}")
    print(f"  Routes: {len(schema['properties']['inference']['properties']['best_candidate_route_id']['enum'])}")
    print(f"  Journey stages: {len(schema['properties']['inference']['properties']['journey_stage']['enum'])}")
    print(f"  Problem families: {len(schema['properties']['inference']['properties']['problem_family']['enum'])}")
    print(f"  Task IDs: {len(schema['properties']['evidence']['properties']['task']['enum'])}")


if __name__ == "__main__":
    main()
