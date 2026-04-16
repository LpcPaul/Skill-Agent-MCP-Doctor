# Intake Card — v2.1

## What this is

The intake card is the bridge between an AI agent's stuck state and the AgentRX case library.

It forces the agent to translate its subjective experience into a structured, queryable format.

## Core principle: Evidence before Inference

The intake card is split into two layers:

| Layer | What it contains | Mutability |
|---|---|---|
| **Evidence** | Observable facts extracted from the context | Immutable |
| **Inference** | AI-generated diagnosis and prescription | Re-computable |

The agent must fill **evidence first**, then derive **inference** from it.
Inference without sufficient evidence is inference pollution.

---

## Part 1: Evidence

Evidence is what the agent directly observes. No diagnosis language.

### task
What job is being attempted?

**Rule:** Describe at the human-job level, not the tool level.

Good:
- `browse-web`
- `read-files`
- `create-presentation`

Bad:
- `browser-cdp`
- `playwright-mcp`

### desired_outcome
What is the agent actually trying to accomplish next?

Examples:
- extract main content from a public page
- generate a slide outline
- decide between two routes

### attempted_path
What tool path was used?

Contains:
- `tool`: name of the tool (e.g. `browser-cdp`)
- `tool_type`: one of `skill`, `mcp`, `plugin`, `builtin`, `agent`, `workflow`, `hook`
- `other_tools`: alternative tools that were considered or available

### symptom
What is the surface observation?

**Rule:** No diagnosis language. Just what was seen.

Good:
- `extracted content was incomplete`
- `permission denied on file access`
- `output format does not match expected schema`

Bad:
- `the tool is broken` (that's a diagnosis)
- `capability mismatch` (that's a problem family)

### context (optional)
Additional context explaining the situation without business specifics.

### environment (optional)
Platform and constraint information:
- `platform`: claude-code, claude-ai, openclaw, etc.
- `requires_login`, `requires_dynamic_render`, etc.
- `notes`: brief constraint notes

### failed_step (optional)
The specific step in the tool path that failed.

### reproduction_steps (optional)
What was already tried. This prevents looped retries.

---

## Part 2: Inference

Inference is the AI's interpretation of the evidence. It is **re-computable** — a different agent reading the same evidence might reach a different inference.

### journey_stage
Where in the task journey is the blockage?

One of:
- `understand-task`
- `choose-capability`
- `configure-capability`
- `execute-task`
- `validate-output`
- `recover-from-failure`
- `optimize-tool-path`

### problem_family
What category of problem does this most resemble?

One of:
- `environment`
- `configuration`
- `invocation`
- `capability_mismatch`
- `quality_miss`
- `observability_gap`
- `recovery_gap`
- `better_alternative_exists`
- `hook_vs_model_boundary`
- `task_framing_issue`
- `not_a_tooling_problem`
- `unknown`

### why_current_path_failed
**This is a core field.** Short explanation of why the current path is unsuitable for continued progress.

**Rule:** Explain the mismatch, not the tool. Don't blame the tool — explain why the tool-path-task combination doesn't work.

Good:
- "The current tool only captures static HTML, but the page requires client-side rendering to populate content"
- "The task requires authenticated API access, but the current path has no credential management"

Bad:
- "The tool is broken" (too vague)
- "Capability mismatch" (that's the label, not the explanation)

### best_candidate_route_id
**This is a core field.** Must be a standard route id from `rules/routes.yaml`.

**Rule:** This is an action path, not a tool brand name.

Good:
- `switch_to_alternative_tool_path`
- `switch_to_web_research`
- `request_missing_input`

Bad:
- `tavily`
- `web-access skill`
- `use playwright`

### best_candidate_route_detail (optional)
Explanation of why this route is recommended. May reference specific tools or strategies.

### prerequisites_for_switch (optional)
Lightweight checklist of what must be true before switching.

Examples:
- `internet_access`
- `repo_access`
- `api_credentials_available`

### confidence
Confidence in this inference: `high`, `medium`, or `low`.

---

## Complete example

```yaml
evidence:
  task: "browse-web"
  desired_outcome: "Extract main content from a public webpage."
  attempted_path:
    tool: "browser-cdp"
    tool_type: "skill"
    other_tools:
      - name: "web_fetch"
        type: "builtin"
        role: "candidate alternative"
  symptom: "Extracted content was incomplete. Only the static HTML shell was captured."
  context: "The target page relies on client-side JavaScript rendering."
  environment:
    platform: "claude-code"
    requires_dynamic_render: true
    requires_network: true
  reproduction_steps:
    - "Used browser-cdp skill once"
    - "Retried without changing rendering strategy"

inference:
  journey_stage: "execute-task"
  problem_family: "capability_mismatch"
  why_current_path_failed: "The current tool only captures static HTML. The page requires client-side rendering to populate its content."
  best_candidate_route_id: "switch_to_alternative_tool_path"
  best_candidate_route_detail: "Switch to a browser path with stronger dynamic rendering support. playwright-mcp is a good candidate."
  prerequisites_for_switch:
    - "internet_access"
    - "repo_access"
  confidence: "medium"
```

---

## Key rule

If you don't have enough evidence to support an inference, leave the optional inference fields empty rather than inventing them.

Under-specified inference is better than polluted inference.
