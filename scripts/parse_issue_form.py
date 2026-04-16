#!/usr/bin/env python3
"""
AgentRX — Parse Issue Form & Assemble v2.1 Case JSON

Reads a GitHub issue body produced by the case_report.yml form,
extracts all structured fields, and produces a valid v2.1 case JSON.

Usage:
    python3 scripts/parse_issue_form.py --body-file /path/to/issue_body.txt
    # Output: writes /tmp/case_from_issue.json and prints path
"""

import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone


def parse_markdown_field(body: str, label: str) -> str:
    """Extract a field value from GitHub issue form markdown."""
    escaped = re.escape(label)
    # Match field value until next ### heading or end of string
    pattern = rf'^### {escaped}\s*\n([\s\S]*?)(?=^### |\Z)'
    match = re.search(pattern, body, re.MULTILINE)
    if match:
        val = match.group(1).strip()
        # Remove trailing content that belongs to next ## section (not ###)
        val = re.split(r'\n## ', val)[0].strip()
        if val == '_No response_':
            return ''
        return val
    return ''


def parse_dropdown(body: str, label: str) -> str:
    """Extract a dropdown selection (strip leading '- ')."""
    val = parse_markdown_field(body, label)
    return re.sub(r'^-\s*', '', val).strip()


def parse_multiline(body: str, label: str) -> list[str]:
    """Extract a multiline field as a list of non-empty lines."""
    val = parse_markdown_field(body, label)
    lines = []
    for line in val.split('\n'):
        cleaned = re.sub(r'^-\s*', '', line).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def parse_environment_notes(notes_text: str) -> dict:
    """Parse environment notes into structured environment object."""
    env: dict = {'platform': 'other'}
    if not notes_text:
        return env
    platform_match = re.search(r'[Pp]latform:\s*(\S+)', notes_text)
    if platform_match:
        env['platform'] = platform_match.group(1)
    if 'dynamic render' in notes_text.lower():
        env['requires_dynamic_render'] = True
    if 'network' in notes_text.lower():
        env['requires_network'] = True
    if 'login' in notes_text.lower():
        env['requires_login'] = True
    if 'filesystem' in notes_text.lower():
        env['requires_local_filesystem'] = True
    if 'deterministic' in notes_text.lower():
        env['requires_deterministic_execution'] = True
    env['notes'] = notes_text
    return env


def assemble_case(body: str) -> dict:
    """Assemble a v2.1 case JSON from issue form body."""
    # ── Evidence ──
    task = parse_markdown_field(body, 'Task')
    desired_outcome = parse_markdown_field(body, 'Desired outcome')
    attempted_tool = parse_markdown_field(body, 'Attempted tool')
    tool_type = parse_dropdown(body, 'Tool type') or 'unknown'
    symptom = parse_markdown_field(body, 'Symptom')
    reproduction_steps = parse_multiline(body, 'Reproduction steps')
    context = parse_markdown_field(body, 'Context (optional)')
    environment_notes = parse_markdown_field(body, 'Environment notes (optional)')
    failed_step = parse_markdown_field(body, 'Failed step (optional)')
    artifacts_used = parse_multiline(body, 'Artifacts used (optional)')

    # ── Inference ──
    journey_stage = parse_dropdown(body, 'Journey stage') or 'unknown'
    problem_family = parse_dropdown(body, 'Problem family') or 'unknown'
    why_current_path_failed = parse_markdown_field(body, 'Why current path failed')
    best_candidate_route_id = parse_dropdown(body, 'Best candidate route id')
    best_candidate_route_detail = parse_markdown_field(body, 'Route detail (optional)')
    prerequisites_for_switch = parse_multiline(body, 'Prerequisites for switch (optional)')
    confidence = parse_dropdown(body, 'Confidence') or 'medium'

    # ── Resolution ──
    outcome = parse_dropdown(body, 'Outcome') or 'unknown'
    follow_up_notes = parse_markdown_field(body, 'Follow-up notes (optional)')

    # ── Metadata ──
    source = parse_dropdown(body, 'Source') or 'user-reported'
    tags_raw = parse_markdown_field(body, 'Tags')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

    # ── Build v2.1 case ──
    task_slug = re.sub(r'\s+', '-', task).lower()[:20] if task else 'unknown'
    case_id = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{task_slug}-{int(datetime.now(timezone.utc).timestamp()) % 10000:04d}"

    evidence = {
        'task': task,
        'desired_outcome': desired_outcome,
        'attempted_path': {
            'tool': attempted_tool,
            'tool_type': tool_type,
        },
        'symptom': symptom,
    }
    if reproduction_steps:
        evidence['reproduction_steps'] = reproduction_steps
    if context:
        evidence['context'] = context
    env_obj = parse_environment_notes(environment_notes)
    if len(env_obj) > 1:
        evidence['environment'] = env_obj
    if failed_step:
        evidence['failed_step'] = failed_step
    if artifacts_used:
        evidence['artifacts_used'] = artifacts_used

    inference = {
        'journey_stage': journey_stage,
        'problem_family': problem_family,
        'why_current_path_failed': why_current_path_failed,
        'best_candidate_route_id': best_candidate_route_id,
        'confidence': confidence,
    }
    if best_candidate_route_detail:
        inference['best_candidate_route_detail'] = best_candidate_route_detail
    if prerequisites_for_switch:
        inference['prerequisites_for_switch'] = prerequisites_for_switch

    resolution = {
        'outcome': outcome,
    }
    if follow_up_notes:
        resolution['follow_up_notes'] = follow_up_notes

    return {
        'schema_version': '2.1',
        'id': case_id,
        'title': f"{task} {journey_stage} {problem_family}",
        'summary': why_current_path_failed,
        'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'tags': tags,
        'evidence': evidence,
        'inference': inference,
        'resolution': resolution,
        'source': source,
        'verified': False,
        'related_cases': [],
    }


def main():
    parser = argparse.ArgumentParser(description='Assemble v2.1 case JSON from GitHub issue form body')
    parser.add_argument('--body-file', required=True, help='Path to file containing the issue body')
    parser.add_argument('--output', default='/tmp/case_from_issue.json', help='Output JSON path')
    args = parser.parse_args()

    body_path = Path(args.body_file)
    if not body_path.exists():
        print(f"ERROR: File not found: {body_path}", file=sys.stderr)
        sys.exit(1)

    body = body_path.read_text()
    case = assemble_case(body)

    out_path = Path(args.output)
    out_path.write_text(json.dumps(case, indent=2, ensure_ascii=False))
    print(f"Case assembled: {out_path}")
    print(f"  ID: {case['id']}")
    print(f"  Task: {case['evidence']['task']}")
    print(f"  Route: {case['inference']['best_candidate_route_id']}")


if __name__ == '__main__':
    main()
