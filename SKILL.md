---
name: agentrx
description: >
  Diagnose why the current AI tool path is stuck or underperforming.
  Use when the agent is blocked, uncertain which tool family to use,
  suspects a better alternative exists, or needs to turn a messy failure
  into a structured next-step decision.
  Covers skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks.
tags: [meta, diagnosis, governance, task-routing, tool-selection, recovery]
---

# AgentRX

You are a **task-first diagnosis and action-navigation layer** for AI agents.

## When to activate

Activate when ANY of these is true:
- A tool execution failed or returned unusable output
- The user rejected the result ("wrong", "retry", "not this")
- The agent switched tools mid-task
- The agent is uncertain between multiple tool families
- Output succeeded technically but missed the real task goal
- The agent suspects the current tool is not the best available choice

Do NOT use for: general coding, broad research, normal execution when the agent already knows what to do.

---

## Phase 1 — Build the intake card

Before searching for answers, fill this structure.

```yaml
platform: ""
task_category: ""
task_goal: ""
journey_stage: ""
observed_symptom: ""
tool_triggered: ""
tool_type: ""
other_tools_in_path: []
suspected_problem_family: ""
constraints:
  requires_login: false
  requires_dynamic_render: false
  requires_local_filesystem: false
  requires_network: false
  requires_deterministic_execution: false
  notes: ""
attempted_actions: []
desired_outcome: ""
diagnosis_summary: ""
confidence: "high|medium|low"
```

**Field rules:**
- `task_category`: describe the human job, not the tool name (e.g. `browse-web`, not `browser-cdp`)
- `journey_stage`: one of `understand-task`, `choose-capability`, `configure-capability`, `execute-task`, `validate-output`, `recover-from-failure`, `optimize-tool-path`
- `observed_symptom`: surface symptom only, no diagnosis
- `suspected_problem_family`: one of `environment`, `configuration`, `invocation`, `capability_mismatch`, `quality_miss`, `observability_gap`, `recovery_gap`, `better_alternative_exists`, `hook_vs_model_boundary`, `task_framing_issue`, `not_a_tooling_problem`, `unknown`
- `desired_outcome`: what the agent actually needs next (e.g. "choose a better tool path", "recover with a stronger alternative")

See `docs/INTAKE_CARD.md` for detailed field explanations and examples.

---

## Phase 2 — Search

After the intake card is complete, search in this order:

1. **Local index** — `cases/index.json` (prioritize by task_category, then journey_stage, then suspected_problem_family)
2. **Task documents** — `docs/ARCHITECTURE.md`, `rules/task_taxonomy.yaml`, `rules/journey_stages.yaml`, `rules/problem_families.yaml`
3. **Remote library** — GitHub issues or remote index if local data is insufficient

Do NOT search only by the currently failing tool unless the intake already makes that the main signal.

---

## Phase 3 — Output format

Structure your response as:

1. **Task understanding** — what the agent was trying to do
2. **Where the blockage is** — journey_stage + observed_symptom
3. **Most likely problem family** — suspected_problem_family
4. **Recommended next action** — one primary choice from:
   - `adjust_current_tool_invocation`
   - `switch_tool_within_same_task`
   - `inspect_environment_or_permissions`
   - `move_to_hook_or_workflow`
   - `reframe_task_before_retry`
   - `ask_for_one_missing_constraint`
   - `stop_tooling_changes_not_a_tool_issue`
5. **Candidate tools / routes** — with brief tradeoff notes
6. **Whether to submit a case** — only if the user agrees

See `docs/` for the full taxonomy and reasoning framework.

---

## Phase 4 — Case contribution

If the user agrees, create a redacted case report.

### Privacy rules

Never include: company names, user names, private URLs, local file paths, business data, code or document contents from private work.

### What to include

- platform, task_category, journey_stage, symptom
- tool_triggered, tool_type, suspected_problem_family
- desired_outcome, recommended_next_step, recommendation_detail
- alternatives_considered (with better_for and tradeoff)
- outcome, confidence
- abstract constraints and attempted actions

The case must help another agent understand the task, the blockage, and the recommended action — without exposing what private business work was being done.

Run `scripts/redact.py --input /tmp/case.json` before any submission.
