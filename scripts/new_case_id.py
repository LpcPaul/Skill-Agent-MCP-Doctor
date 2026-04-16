#!/usr/bin/env python3
"""
AgentRX — Generate a new case ID.

Output format: YYYY-MM-DD-{task}-{shortuuid8}
Example: 2026-04-16-browse-web-a13f92cd

Usage:
    python3 scripts/new_case_id.py --task browse-web
    python3 scripts/new_case_id.py --task code-editing
"""

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone


def generate_short_uuid8() -> str:
    """Generate an 8-character hex ID from current time + random seed."""
    seed = f"{time.time_ns()}–{id(generate_short_uuid8)}"
    return hashlib.md5(seed.encode()).hexdigest()[:8]


def generate_case_id(task: str) -> str:
    """Generate a case ID in the format YYYY-MM-DD-{task}-{shortuuid8}."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    task_slug = task.lower().replace("_", "-").replace(" ", "-")
    # Truncate task slug to avoid overly long IDs
    task_slug = task_slug[:30]
    short_id = generate_short_uuid8()
    return f"{date_str}-{task_slug}-{short_id}"


def main():
    parser = argparse.ArgumentParser(description="Generate a new case ID.")
    parser.add_argument("--task", required=True, help="Task ID (e.g. browse-web, code-editing)")
    parser.add_argument("--quiet", action="store_true", help="Only output the ID, no extra text")
    args = parser.parse_args()

    case_id = generate_case_id(args.task)

    if args.quiet:
        print(case_id)
    else:
        print(f"Generated case ID: {case_id}")
        print(f"  Format: YYYY-MM-DD-<task>-<shortuuid8>")
        print(f"  Example filename: cases/{case_id}.json")


if __name__ == "__main__":
    main()
