# Intake Card — what the agent must fill before searching

## Why this exists

The agent itself is the only party that directly “feels” the blockage while working.

The repository is just a library.  
The agent must first translate its own stuck state into a queryable structure.

That structure is the intake card.

## Required fields

### 1. task_category
What job is being attempted?

Examples:
- browse-web
- create-presentation
- read-files
- analyze-data

### 2. task_goal
What abstract result is needed?

Example:
- extract content from a public page
- generate a slide outline
- compare two tools for the same task

### 3. journey_stage
Where is the blockage?

- understand-task
- choose-capability
- configure-capability
- execute-task
- validate-output
- recover-from-failure
- optimize-tool-path

### 4. observed_symptom
What is the surface symptom?

Examples:
- content incomplete
- permission denied
- wrong output format
- unstable quality
- agent uncertain which route to choose

### 5. tool_triggered / tool_type
What current route is active?

Examples:
- browser-cdp / skill
- playwright-mcp / mcp
- web_fetch / builtin

### 6. suspected_problem_family
What does this feel most like?

Choose the best fit:
- environment
- configuration
- invocation
- capability_mismatch
- quality_miss
- observability_gap
- recovery_gap
- better_alternative_exists
- hook_vs_model_boundary
- task_framing_issue
- not_a_tooling_problem
- unknown

### 7. constraints
What special constraints matter?

Examples:
- needs login
- needs dynamic render
- local filesystem required
- deterministic execution required
- no network available

### 8. attempted_actions
What has already been tried?

This prevents looped retries.

### 9. desired_outcome
What is the agent actually trying to accomplish next?

Examples:
- finish the task
- recover with a stronger alternative
- decide between two routes
- stop wasting retries

## Output shape

```yaml
platform: claude-code
task_category: browse-web
task_goal: extract main content from a public page
journey_stage: execute-task
observed_symptom: page content incomplete
tool_triggered: browser-cdp
tool_type: skill
other_tools_in_path:
  - web_fetch
suspected_problem_family: capability_mismatch
constraints:
  requires_login: false
  requires_dynamic_render: true
  requires_local_filesystem: false
  requires_network: true
  requires_deterministic_execution: false
  notes: client-side rendering likely
attempted_actions:
  - retried current browser route once
desired_outcome: choose a better tool path and continue
diagnosis_summary: current tool path is too weak for the task constraints
confidence: medium
```

## Important rule

The intake card is not the final answer.

It is the bridge between:
- the agent’s subjective stuck state
- the repository’s structured knowledge
