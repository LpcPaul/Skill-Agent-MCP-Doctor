#!/usr/bin/env bash
# AgentRX — Tool error intake prefill hook (legacy)
#
# NOTE: For automated Claude Code integration, use hooks/claude_code/post_tool_error.py
# which runs as a PostToolUse hook and automatically retrieves similar cases.
#
# This script is kept for standalone/manual use.
#
# Usage: When a tool execution fails, this script generates an intake
# skeleton JSON with pre-filled evidence fields. The agent can then
# complete the remaining fields (desired_outcome, symptom detail, inference).
#
# Example:
#   ./hooks/tool_error_intake_prefill.sh "browse-web" "web_fetch" "builtin" "Static HTML returned empty" "Static HTML fetch returned page skeleton without JavaScript-rendered content"
#
# Arguments:
#   $1 task           (e.g. browse-web, code-editing)
#   $2 tool_name      (e.g. web_fetch, python)
#   $3 tool_type      (skill|mcp|plugin|builtin|agent|workflow|hook|unknown)
#   $4 failed_step    (short description)
#   $5 symptom        (surface-level observation)
#
# Output: JSON to stdout — an intake skeleton ready for the agent to complete.

set -euo pipefail

TASK="${1:-}"
TOOL_NAME="${2:-}"
TOOL_TYPE="${3:-unknown}"
FAILED_STEP="${4:-}"
SYMPTOM="${5:-}"

if [ -z "$TASK" ] || [ -z "$TOOL_NAME" ] || [ -z "$SYMPTOM" ]; then
  echo "Usage: $0 <task> <tool_name> <tool_type> <failed_step> <symptom>" >&2
  exit 1
fi

# Generate case ID
CASE_ID=$(python3 "$(dirname "$0")/../scripts/new_case_id.py" --task "$TASK" --quiet 2>/dev/null || echo "pending")

cat <<EOF
{
  "schema_version": "2.1",
  "id": "${CASE_ID}",
  "title": "${TASK} (pending classification)",
  "summary": "${SYMPTOM}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tags": ["${TASK}", "tool-error"],
  "evidence": {
    "task": "${TASK}",
    "desired_outcome": "",
    "attempted_path": {
      "tool": "${TOOL_NAME}",
      "tool_type": "${TOOL_TYPE}"
    },
    "symptom": "${SYMPTOM}",
    "failed_step": "${FAILED_STEP}",
    "environment": {
      "platform": "claude-code"
    }
  },
  "inference": {},
  "source": "hook-generated",
  "verified": false,
  "related_cases": []
}
EOF
