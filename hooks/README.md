# Hooks — Deterministic Layer for Skill Doctor

Hooks are the **deterministic** complement to skill-doctor's model-based diagnosis.
While skills rely on the model's judgment to detect and classify failures,
hooks run automatically at defined lifecycle points to catch errors the model might miss.

## When to Use Hooks vs Skills

| Scenario | Use |
|---|---|
| Tool execution fails | **Hook** — exit code ≠ 0 is deterministic |
| Output quality is poor | **Skill** — model must judge quality |
| Wrong skill was triggered | **Skill** — model must understand routing |
| Permission denied on file | **Hook** — filesystem error is deterministic |
| Skill instructions too vague | **Skill** — model must analyze ambiguity |

## Available Hooks

### `tool_error_autodiagnose.sh`

Automatically triggers skill-doctor diagnosis when any tool command fails.

**Setup:** Configure in your Claude Code hooks configuration:
```json
{
  "hooks": {
    "tool_error": "~/.claude/skills/skill-doctor/hooks/tool_error_autodiagnose.sh"
  }
}
```

**Behavior:**
1. Detects tool failure via exit code
2. Builds a diagnostic case JSON
3. Runs `redact.py` to ensure no sensitive data leaks
4. Checks `cases/index.json` for known similar failures
5. Prints diagnosis summary for the agent to act on

**Environment Variables:**
| Variable | Description |
|---|---|
| `CLAUDE_HOOK_EVENT` | Event type (e.g. `tool_error`) |
| `CLAUDE_HOOK_TOOL` | Name of the failed tool/command |
| `CLAUDE_HOOK_ERROR` | Error message from stderr |
| `CLAUDE_HOOK_COMMAND` | The command that was attempted |
| `CLAUDE_HOOK_EXIT_CODE` | Exit code of the failed command |

## Writing Custom Hooks

Follow this pattern:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Find skill-doctor
SKILL_BASE="${SKILL_DOCTOR_PATH:-$(find ~/.claude/skills/skill-doctor -maxdepth 0 -type d 2>/dev/null | head -1)}"

# 2. Check if this event should trigger
if [ "$CLAUDE_HOOK_EVENT" != "your_event" ]; then
    exit 0
fi

# 3. Build case JSON
# 4. Run redact.py --dry-run
# 5. Output diagnosis for the agent
```

## Future Hooks

- **`context_overflow_check.sh`** — Monitor conversation length, warn when skill instructions may be lost
- **`skill_routing_audit.sh`** — Log which skills were auto-invoked vs manually invoked, detect routing patterns
