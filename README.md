# Skill-Agent-MCP Docter

> Formerly **Skill Doctor**  
> A task-first diagnosis and action-navigation layer for AI tools: skills, MCP servers, plugins, built-in tools, agents, and workflows.

## Why this project changed

The old project was designed around the question:

- “Which skill failed?”
- “Which failure type does this belong to?”

That worked only when the agent already knew **which skill** was involved.

But real failures usually begin from a messier place:

- “I’m trying to browse a page and the content is incomplete.”
- “I generated a document, but the output is wrong.”
- “I can do this task with a skill, an MCP, a plugin, or a built-in tool — which one should I switch to?”
- “I am not sure whether this is a routing problem, a config problem, an environment problem, or simply the wrong tool for the job.”

So the project has been redesigned around a different principle:

> **Start from the task, then locate the stage, then classify the problem family, then choose the next action.**

This repository is no longer only about “skill governance.”  
It is about **AI tool-path diagnosis and next-step recommendation**.

## Core positioning

Skill-Agent-MCP Docter is a **meta-skill / governance layer** that helps an AI agent when it is stuck.

It does four things:

1. **Intake** — force the agent to describe its own blockage in a structured way.
2. **Navigate** — route the problem through a task-first knowledge architecture.
3. **Recommend** — propose the most suitable next action, not just a label.
4. **Contribute** — turn successful or failed recovery paths into reusable cases.

## What it covers

This project now covers failures and decision paths involving:

- **skill**
- **mcp**
- **plugin**
- **builtin**
- **agent**
- **workflow / hook / deterministic path**

The scope is still bounded.

This is **not** a universal benchmark site for all AI tools.  
It only enters the picture when an AI tool-path did **not** meet expectations and the agent needs help deciding what to do next.

## New mental model

Do **not** organize from:

`tool name -> failure type -> remedy`

Organize from:

`task -> journey stage -> problem family -> next action -> candidate tools/cases`

That means the system is designed for this flow:

1. The agent notices it is stuck.
2. The agent performs a **local self-diagnosis** first.
3. The agent converts its blockage into a standard intake card.
4. The agent navigates the library by:
   - task category
   - journey stage
   - suspected problem family
5. The agent retrieves:
   - similar cases
   - known tradeoffs
   - recommended next actions
6. The agent chooses one of the candidate actions.
7. The result is optionally written back as a new case.

## New action path for the agent

When activated, the agent should not immediately search the repo by tool name.

It should first answer:

1. **What task am I trying to complete?**
2. **Which stage am I stuck in?**
3. **What symptom am I observing?**
4. **What problem family does this most resemble?**
5. **What have I already tried?**
6. **What constraints matter here?**
7. **What outcome do I actually need next?**

Only after this intake step should it search the local index or remote case library.

## Repository structure (v2)

```text
.github/
  ISSUE_TEMPLATE/
    case_report.yml
  workflows/
    validate_case.yml

cases/
  README.md
  index.json
  templates/
    case.example.json

docs/
  ARCHITECTURE.md
  CASE_COLLECTION_PLAN.md
  INTAKE_CARD.md
  MIGRATION_GUIDE.md
  REPO_AUDIT.md

hooks/
  README.md

rules/
  failure_types.yaml          # backward-compatible alias / migration note
  journey_stages.yaml
  problem_families.yaml
  task_taxonomy.yaml

schema/
  case.schema.json

CONTRIBUTING.md
README.md
SKILL.md
```

## What changed from the old version

### Old model
- centered on `skill_triggered`
- organized cases by `by-skill/` and `by-type/`
- retrieved mostly by `skill_triggered + failure_type`
- treated many failures as “skill failures”

### New model
- centered on `task_category + journey_stage + suspected_problem_family`
- stores the active tool path, not just the failing skill
- covers alternative tools in the same task
- recommends the **next action** rather than only classifying the cause
- asks the agent to perform **local self-diagnosis first**

## Install

Until you rename the GitHub repository itself, you can still clone from the current slug and place it under the new local folder name.

### Claude Code

```bash
git clone https://github.com/LpcPaul/skill-doctor.git ~/.claude/skills/skill-agent-mcp-docter
```

### OpenClaw / ClawHub

```bash
git clone https://github.com/LpcPaul/skill-doctor.git ~/.openclaw/skills/skill-agent-mcp-docter
```

### Codex / Cursor / other skill-compatible runtimes

```bash
git clone https://github.com/LpcPaul/skill-doctor.git ~/.codex/skills/skill-agent-mcp-docter
```

When the GitHub repository slug is renamed, replace the URL accordingly.

## Trigger conditions

This project should activate when any of the following happens:

- the current tool-path fails during execution
- the output clearly misses the user’s intent
- the agent switches tools mid-task
- the agent is unsure which tool family to use
- the agent suspects a better alternative exists
- the agent is stuck deciding whether the issue is:
  - configuration
  - environment
  - invocation
  - capability mismatch
  - quality miss
  - observability gap
  - recovery gap
  - wrong task framing
  - a deterministic workflow / hook boundary issue

## What this project should recommend

The recommendation should usually be one of these action types:

- keep current tool, but adjust invocation
- keep task route, but switch tool
- stop switching tools and inspect environment/config first
- move from model judgment to hook/workflow
- reframe the task before retrying
- ask the user for one missing constraint
- conclude it is **not** a tooling problem

## Cases

Cases are now task-first.  
They should preserve the real user journey:

- what the agent was trying to do
- which tool path it took
- what symptom appeared
- what alternatives existed
- what action resolved or improved the situation

See:
- `docs/CASE_COLLECTION_PLAN.md`
- `docs/INTAKE_CARD.md`
- `schema/case.schema.json`

## Roadmap

- [x] Redefine project scope from skill-only to multi-tool diagnosis
- [x] Replace failure-first retrieval with intake-first navigation
- [x] Redesign schema for task / stage / problem-family routing
- [x] Rewrite contribution path around real AI journey cases
- [ ] Migrate legacy case files into v2 schema
- [ ] Update deterministic redaction and validation scripts for v2 fields
- [ ] Auto-generate task-first index from accepted cases
- [ ] Add benchmark-style case bundles for top task categories
- [ ] Publish a reusable cross-agent “stuck-state intake” format

## License

MIT
