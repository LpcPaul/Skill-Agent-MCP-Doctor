# AgentRX — Claude Code Hooks

Real Claude Code `PostToolUse` hooks that activate automatically when the agent gets stuck.

## How it works

The `post_tool_error.py` hook runs after every tool use. It activates only when a concrete failure signal is detected:

1. **Error loop detection** — same tool failed ≥2 times in the last 3 minutes
2. **Error pattern in response** — tool response contains error/failed/exception patterns
3. **User rejection** — user's last message matches `^(不对|错了|retry|再来|wrong|no|nope)\b`

When activated, it:
1. Constructs an intake card from observable context (evidence only)
2. Retrieves similar cases from the library (excluding synthetic seeds by default)
3. Injects retrieval results into the agent's next context as `additionalContext`

## Setup

### Option A: Project-level configuration (recommended)

Add this to `.claude/settings.json` in your project:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/hooks/claude_code/post_tool_error.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

### Option B: Global configuration

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/AgentRX/hooks/claude_code/post_tool_error.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

### Option C: Skill-level (if AgentRX is installed as a skill)

Add to `~/.claude/skills/agentrx/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/../skills/agentrx/hooks/claude_code/post_tool_error.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

## State management

Error tracking state is stored in `~/.claude/agentrx-state/` (configurable via `CLAUDE_CODE_STATE_DIR` env var). Each tool's error history is tracked separately with automatic pruning of entries older than 3 minutes.

## Testing

To verify the hook is working:

1. Enable it in your settings.json
2. Run a command that will fail (e.g. `python3 -c "raise Exception('test')"`)
3. Run it again
4. On the second failure, you should see similar case retrieval results injected into the agent context

## Legacy hook

`hooks/tool_error_intake_prefill.sh` is still available as a standalone intake skeleton generator. For the full automated experience, use the Claude Code hook above.
