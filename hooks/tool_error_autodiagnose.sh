#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
# Claude Code Hook — Auto-trigger Skill Doctor on Tool Error
# ─────────────────────────────────────────────────────
#
# This hook watches for tool execution failures and automatically
# invokes the skill-doctor diagnostic flow.
#
# Install: Copy this to your Claude Code hooks directory and configure
#          your agent to run it after tool execution errors.
#
# Usage: Called by Claude Code hook system when a tool fails.
#   Expects environment variables:
#     CLAUDE_HOOK_EVENT    — event type (e.g. "tool_error")
#     CLAUDE_HOOK_TOOL     — name of the failed tool
#     CLAUDE_HOOK_ERROR    — error message / stderr
#     CLAUDE_HOOK_COMMAND  — the command that was attempted
#     CLAUDE_HOOK_EXIT_CODE — exit code of the failed command
#
# ─────────────────────────────────────────────────────

set -euo pipefail

# ── Find skill-doctor base path ──
SKILL_BASE="${SKILL_DOCTOR_PATH:-}"
if [ -z "$SKILL_BASE" ]; then
    SKILL_BASE="$(find ~/.claude/skills/skill-doctor ~/.codex/skills/skill-doctor /mnt/skills/skill-doctor .claude/skills/skill-doctor -maxdepth 0 -type d 2>/dev/null | head -1)"
fi

if [ -z "$SKILL_BASE" ] || [ ! -d "$SKILL_BASE" ]; then
    echo "[skill-doctor hook] skill-doctor not found, skipping diagnosis" >&2
    exit 0
fi

# ── Read hook inputs ──
HOOK_EVENT="${CLAUDE_HOOK_EVENT:-}"
HOOK_TOOL="${CLAUDE_HOOK_TOOL:-}"
HOOK_ERROR="${CLAUDE_HOOK_ERROR:-}"
HOOK_COMMAND="${CLAUDE_HOOK_COMMAND:-}"
HOOK_EXIT_CODE="${CLAUDE_HOOK_EXIT_CODE:-}"

# Only act on tool errors
if [ "$HOOK_EVENT" != "tool_error" ]; then
    exit 0
fi

# ── Build a diagnostic case ──
CASE_ID="$(date +%Y-%m-%d)-hook$(openssl rand -hex 3 2>/dev/null || echo $RANDOM | md5sum | head -c 6)"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > /tmp/skill_doctor_hook_case.json <<EOFCASE
{
  "case_id": "${CASE_ID}",
  "timestamp": "${TIMESTAMP}",
  "platform": "claude-code",
  "skill_triggered": "${HOOK_TOOL}",
  "skill_version": "unknown",
  "other_active_skills": [],
  "failure_type": "tool_error",
  "failure_signature": "Tool '${HOOK_TOOL}' failed with exit code ${HOOK_EXIT_CODE} when executing: ${HOOK_COMMAND}",
  "environment": {
    "model": "${CLAUDE_MODEL:-unknown}",
    "os": "$(uname -s | tr '[:upper:]' '[:lower:]')",
    "context_note": "Hook auto-triggered on tool error"
  },
  "user_correction": "No user action yet — hook auto-generated",
  "remedy": "Investigate tool error: exit_code=${HOOK_EXIT_CODE}, tool=${HOOK_TOOL}, error=${HOOK_ERROR}",
  "remedy_type": "not_skill_issue",
  "confidence": "medium",
  "verified": false,
  "_hook_generated": true
}
EOFCASE

# ── Run redaction ──
"${SKILL_BASE}/scripts/redact.py" --input /tmp/skill_doctor_hook_case.json --dry-run 2>/dev/null
REDACT_EXIT=$?

if [ $REDACT_EXIT -eq 2 ]; then
    echo "[skill-doctor hook] Case blocked by redaction — contains sensitive content" >&2
    rm -f /tmp/skill_doctor_hook_case.json
    exit 0
fi

# ── Present diagnosis to agent ──
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🩺 Skill Doctor — Hook Auto-Diagnosis"
echo "═══════════════════════════════════════════════════════"
echo "  Tool failed: ${HOOK_TOOL}"
echo "  Exit code:   ${HOOK_EXIT_CODE}"
echo "  Command:     ${HOOK_COMMAND}"
echo ""

# ── Check local case index for similar failures ──
if [ -f "${SKILL_BASE}/cases/index.json" ]; then
    # Extract matching cases (tool_error type for this tool)
    MATCH_COUNT=$(python3 -c "
import json
with open('${SKILL_BASE}/cases/index.json') as f:
    idx = json.load(f)
matches = [c for c in idx.get('cases', []) if c.get('failure_type') == 'tool_error' and c.get('skill_triggered') == '${HOOK_TOOL}']
print(len(matches))
" 2>/dev/null || echo "0")

    if [ "$MATCH_COUNT" -gt 0 ]; then
        echo "  📋 Found ${MATCH_COUNT} known case(s) for ${HOOK_TOOL} tool errors."
        echo "  Checking remedies..."
        python3 -c "
import json
with open('${SKILL_BASE}/cases/index.json') as f:
    idx = json.load(f)
for c in idx.get('cases', []):
    if c.get('failure_type') == 'tool_error' and c.get('skill_triggered') == '${HOOK_TOOL}':
        print(f\"    - {c.get('remedy', 'No remedy listed')}\")
" 2>/dev/null || true
    else
        echo "  No known cases found for this tool failure pattern."
    fi
fi

echo ""
echo "  Case file: /tmp/skill_doctor_hook_case.json"
echo "═══════════════════════════════════════════════════════"
echo ""

# Leave the case file for the agent to review and optionally submit
exit 0
