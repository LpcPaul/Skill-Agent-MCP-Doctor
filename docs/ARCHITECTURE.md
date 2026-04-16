# Architecture — Skill-Agent-MCP Docter

## One sentence summary

This project is a **stuck-state navigation system** for AI agents.

It is not just a case database.  
It is a way to turn a messy failure into a structured next-step decision.

## The old mistake

A skill-first architecture assumes the agent can already answer:

- which skill was involved
- what failure label applies

That assumption is often false.

Agents usually feel the problem first as a symptom:

- incomplete content
- wrong output shape
- permission denied
- unstable result
- unsure which tool to use
- repeated retries with no progress

That is why the new architecture starts from the agent’s **stuck state**, not from the tool name.

## The new architecture

```text
stuck state
  -> local self-diagnosis
  -> intake card
  -> task-first navigation
  -> candidate actions
  -> execution
  -> optional case contribution
```

## The four layers

### 1. Intake layer
Purpose:
- force the agent to describe the blockage in a common language

Questions:
- what task is this
- what stage is stuck
- what symptom is visible
- what tool path is active
- what has already been tried
- what constraints matter

Output:
- a standard intake card

### 2. Navigation layer
Purpose:
- route the intake into the right zone of the library

Order:
1. task category
2. journey stage
3. suspected problem family
4. active tool path
5. recommendation type

### 3. Resolution layer
Purpose:
- tell the agent what to do next

The first output is not a case ID.
The first output is a **next action type**.

Examples:
- adjust current invocation
- switch tool
- inspect environment
- move to workflow/hook
- reframe task
- ask one missing constraint
- stop changing tools

### 4. Evidence layer
Purpose:
- support recommendations with real cases and comparisons

A case is evidence.
A taxonomy is navigation.
A recommendation is the operational output.

## Library analogy

The agent should not need to know the exact book title.

It should first be able to say:

- I am in the “browse-web” section
- I am stuck at “execute-task”
- this looks like “capability_mismatch”

Then it can inspect:
- typical symptoms
- stronger tool routes
- similar cases
- common recovery actions

## Why local self-diagnosis is mandatory

If the agent searches too early, retrieval quality collapses.

Raw queries like:
- “browser tool broken”
- “this skill failed”
- “page incomplete”

are too weak.

The intake card improves search precision because it turns the problem into structured signals.

## Design constraint

This architecture must stay finite.

The project does **not** attempt to catalog every AI tool in existence.
Its scope is bounded by one rule:

> only reason about tools in the context of a failed or underperforming task path

That prevents the project from turning into an infinite review site.

## Practical consequence for the repository

This architecture means the repository should prioritize:

- task taxonomy
- journey stages
- problem families
- case schema
- intake instructions
- recommendation types

over:
- giant lists of tools
- unstructured issue dumps
- skill-name-only browsing
