#!/usr/bin/env python3
"""
AgentRX — Claude Code PostToolUse Hook: Tool Error Detection & Case Retrieval

Triggered after a tool use. Detects failure patterns and retrieves similar
cases to help the agent recover.

Activation conditions (any one triggers):
  1. Same tool has failed >=2 times in the last 3 minutes (tracked via state file)
  2. Tool response contains error/failed/error code patterns
  3. User's last message matches rejection pattern: ^(不对|错了|retry|再来|wrong|no|nope)\b

Behavior:
  1. Constructs an intake card JSON (evidence only, from observable context)
  2. Calls retrieve_cases.py --intake <tmpfile> --top-k 3 --exclude-seeds
  3. If no results, retries without --exclude-seeds and marks as low confidence
  4. Injects results into next agent context via stdout JSON

Output format: Claude Code hook protocol (JSON on stdout, exit 0)

See hooks/claude_code/README.md for setup instructions.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

STATE_DIR = Path(os.environ.get("CLAUDE_CODE_STATE_DIR", Path.home() / ".claude" / "agentrx-state"))
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
MAX_RETRIES_WINDOW_SEC = 180  # 3 minutes
MAX_RETRIES_COUNT = 2

# Rejection patterns from user messages
REJECTION_PATTERNS = re.compile(r"^(不对|错了|retry|再来|wrong|no|nope)\b", re.IGNORECASE)

# Error patterns in tool response
ERROR_PATTERNS = [
    re.compile(r"error", re.IGNORECASE),
    re.compile(r"failed", re.IGNORECASE),
    re.compile(r"exception", re.IGNORECASE),
    re.compile(r"traceback", re.IGNORECASE),
    re.compile(r"non-zero exit", re.IGNORECASE),
    re.compile(r"module.*not found", re.IGNORECASE),
    re.compile(r"permission denied", re.IGNORECASE),
    re.compile(r"no such file", re.IGNORECASE),
    re.compile(r"empty.*output", re.IGNORECASE),
]


def read_stdin_json():
    """Read JSON from stdin (Claude Code hook input)."""
    try:
        data = json.load(sys.stdin)
        return data
    except (json.JSONDecodeError, IOError):
        return None


def load_error_state(tool_name: str) -> list[dict]:
    """Load error history for a tool from state file."""
    state_dir = STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"errors-{tool_name}.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return []


def save_error_state(tool_name: str, errors: list[dict]):
    """Save error history for a tool."""
    state_dir = STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"errors-{tool_name}.json"
    # Prune old entries outside the window
    cutoff = time.time() - MAX_RETRIES_WINDOW_SEC
    errors = [e for e in errors if e.get("timestamp", 0) > cutoff]
    with open(state_file, "w") as f:
        json.dump(errors, f)


def check_error_loop(tool_name: str) -> bool:
    """Check if the same tool has failed >=2 times in the last 3 minutes."""
    errors = load_error_state(tool_name)
    return len(errors) >= MAX_RETRIES_COUNT


def record_error(tool_name: str):
    """Record a new error for the tool."""
    errors = load_error_state(tool_name)
    errors.append({"timestamp": time.time()})
    save_error_state(tool_name, errors)


def check_rejection_message(transcript_path: str) -> bool:
    """Check if user's last message matches rejection pattern."""
    if not transcript_path or not Path(transcript_path).exists():
        return False
    try:
        with open(transcript_path) as f:
            transcript = json.load(f)
        # Find last user message
        for event in reversed(transcript.get("events", [])):
            if event.get("type") == "user" and event.get("message"):
                text = event["message"].get("content", "")
                if isinstance(text, list):
                    text = " ".join(
                        t.get("text", "") for t in text if t.get("type") == "text"
                    )
                return bool(REJECTION_PATTERNS.search(text.strip()))
    except (json.JSONDecodeError, IOError, KeyError):
        pass
    return False


def check_error_in_response(tool_response: dict) -> bool:
    """Check if tool response contains error patterns."""
    response_text = json.dumps(tool_response)
    return any(p.search(response_text) for p in ERROR_PATTERNS)


def detect_task_from_context(hook_input: dict) -> str:
    """Try to detect the task category from tool context."""
    tool_name = hook_input.get("tool_name", "").lower()
    tool_input = hook_input.get("tool_input", {})

    # Heuristic mapping from tool name to task
    task_map = {
        "bash": "code-editing",
        "python": "code-editing",
        "read_file": "read-files",
        "edit": "code-editing",
        "write": "code-editing",
        "web_fetch": "browse-web",
        "browser": "browse-web",
        "playwright": "browse-web",
        "search": "search-and-compare-tools",
        "tavily": "search-and-compare-tools",
        "pptx": "create-presentation",
        "chart": "analyze-data",
        "diagram": "create-visual-assets",
    }
    for key, task in task_map.items():
        if key in tool_name:
            return task

    # Default fallback
    return "code-editing"


def build_intake_card(hook_input: dict) -> dict:
    """Build an intake card from hook context (evidence only)."""
    tool_name = hook_input.get("tool_name", "unknown")
    tool_response = hook_input.get("tool_response", {})
    tool_input = hook_input.get("tool_input", {})

    task = detect_task_from_context(hook_input)

    # Extract symptom from tool response
    response_text = json.dumps(tool_response)
    symptom = response_text[:300] if response_text else "Tool execution failed"

    # Build attempted_path
    attempted_path = {"tool": tool_name, "tool_type": "builtin"}

    # Detect environment
    env = {"platform": "claude-code"}
    cwd = hook_input.get("cwd", "")
    if "local" in cwd or "file" in tool_name.lower():
        env["requires_local_filesystem"] = True
    if "web" in tool_name.lower() or "fetch" in tool_name.lower():
        env["requires_network"] = True

    return {
        "evidence": {
            "task": task,
            "desired_outcome": "",
            "attempted_path": attempted_path,
            "symptom": symptom,
            "environment": env,
            "failed_step": f"{tool_name} execution failed",
        }
    }


def retrieve_cases(intake: dict, top_k: int = 3) -> tuple[list[dict], bool]:
    """Retrieve cases, falling back to include seeds if needed."""
    # Write intake to temp file
    tmpfile = Path("/tmp/agentrx-intake.json")
    with open(tmpfile, "w") as f:
        json.dump(intake, f)

    # First try: exclude seeds
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "retrieve_cases.py"),
        "--intake", str(tmpfile),
        "--top-k", str(top_k),
        "--exclude-seeds",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            cases = json.loads(result.stdout)
            if cases:
                return cases, True
        except json.JSONDecodeError:
            pass

    # Fallback: include seeds
    cmd_no_exclude = [
        sys.executable, str(SCRIPTS_DIR / "retrieve_cases.py"),
        "--intake", str(tmpfile),
        "--top-k", str(top_k),
    ]
    result = subprocess.run(cmd_no_exclude, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            cases = json.loads(result.stdout)
            return cases, False
        except json.JSONDecodeError:
            pass

    return [], False


def format_retrieval_output(cases: list[dict], only_seeds: bool) -> str:
    """Format retrieval results for agent context."""
    if not cases:
        return "No similar cases found in the case library."

    lines = []
    if only_seeds:
        lines.append("⚠️ Only seed matches found — these are illustrative examples, not verified experience. Confidence: low.")
    else:
        lines.append(f"🔍 Found {len(cases)} similar case(s) in the case library:")

    for i, case in enumerate(cases, 1):
        case_id = case.get("case_id", "")
        title = case.get("title", "")
        route = case.get("best_candidate_route_id", "")
        is_seed = case.get("is_seed", False)
        score = case.get("score", 0)

        seed_marker = " [seed]" if is_seed else ""
        lines.append(f"\n  {i}. {title}{seed_marker} (score: {score})")
        lines.append(f"     Route: {route}")
        if case.get("summary"):
            lines.append(f"     Summary: {case['summary'][:120]}")

    lines.append("\nUse these cases to inform your next action. The route recommendation is your own inference.")
    return "\n".join(lines)


def main():
    # Read hook input from stdin
    hook_input = read_stdin_json()
    if hook_input is None:
        # Not a valid hook input, pass through
        sys.exit(0)

    hook_event = hook_input.get("hook_event_name", "")
    if hook_event != "PostToolUse":
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "unknown")
    tool_response = hook_input.get("tool_response", {})
    transcript_path = hook_input.get("transcript_path", "")

    # Check activation conditions
    activated = False

    # Condition 1: Error loop detection
    if check_error_in_response(tool_response):
        record_error(tool_name)
        if check_error_loop(tool_name):
            activated = True

    # Condition 2: User rejection message
    if check_rejection_message(transcript_path):
        activated = True

    if not activated:
        sys.exit(0)

    # Build intake card
    intake = build_intake_card(hook_input)

    # Retrieve similar cases
    cases, only_real = retrieve_cases(intake, top_k=3)

    # Format output
    context = format_retrieval_output(cases, not only_real)

    # Output in Claude Code hook protocol
    output = {
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
