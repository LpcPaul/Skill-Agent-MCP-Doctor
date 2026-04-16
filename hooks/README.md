# Hooks — deterministic complements for Skill-Agent-MCP Docter

Hooks are still important in the new architecture, but their role is now more precise.

This project distinguishes between:

- problems that require **model judgment**
- problems that should be handled by **deterministic control**

## Core principle

Use a hook when the action must happen **every time** and should not depend on the model choosing correctly.

Use the diagnosis layer when the agent must reason about:
- task framing
- tool fit
- capability tradeoffs
- output quality
- recovery strategy

## Hook vs diagnosis layer

| Situation | Better fit |
|---|---|
| Command exits non-zero | Hook |
| Permission denied | Hook first, diagnosis second |
| Output looks wrong for the user’s real intent | Diagnosis layer |
| Agent is unsure which tool family to choose | Diagnosis layer |
| Task should always run before deploy/commit/send | Hook / workflow |
| Same task sometimes uses a skill and sometimes an MCP with unpredictable results | Diagnosis layer |
| Security, lint, policy checks | Hook / workflow |
| Need to explain why the current path is the wrong tool for a dynamic/login page | Diagnosis layer |

## Updated role of hooks

Hooks should now be thought of as:

1. **Signal collectors** — capture deterministic failure facts.
2. **Intake helpers** — prefill parts of the intake card.
3. **Guardrails** — enforce actions that must never be optional.

A hook should not try to replace the entire diagnosis layer.

## Recommended hook outputs

When a hook fires, it should ideally emit structured signals that help populate:

- `journey_stage`
- `observed_symptom`
- `tool_triggered`
- `tool_type`
- `constraints`
- `attempted_actions`

## Good examples

### Tool execution hook
Use when:
- a command crashes
- stderr clearly shows permission or dependency failure

The hook should:
- capture raw deterministic facts
- classify obvious environment/config signals
- pass the event into the diagnosis layer as a partially completed intake card

### Workflow boundary hook
Use when:
- a step must always happen
- missing the step creates unacceptable risk

Examples:
- secret scanning
- policy checks
- deployment safeguards
- mandatory formatting/linting
- audit logging

## Bad use of a hook

Do not use a hook as a crude replacement for task reasoning.

For example:
- “Always use browser tool X for browsing” is usually too rigid.
- The better question is whether the task requires:
  - static fetch
  - dynamic render
  - login state
  - local browser session
  - deterministic scraping

That routing choice belongs in the diagnosis layer.

## Future hook ideas

- `tool_error_intake_prefill.sh`
- `environment_probe_prefill.sh`
- `workflow_boundary_guard.sh`
- `output_validation_signal.sh`

## Migration note

Legacy hook docs assumed the repo was mostly about “skill failures.”  
That is no longer the right frame.

Hooks are now part of a broader model:

`deterministic facts -> intake card -> task-first diagnosis -> next action`
