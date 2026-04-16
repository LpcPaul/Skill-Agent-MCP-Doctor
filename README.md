# AgentRX

> 🩺 AI 工具链的急诊科医生
> *A prescription for your AI agent when its tools fail.*
> 覆盖 skill、MCP server、插件、内置工具、agent、workflow、hook。**任务优先，不是工具优先。**

## 你是不是也遇到过这些情况：

> 你装了各种工具——skill、MCP server、插件——但每次出问题时，AI 总要在工具之间来回试错、切换、重试。时间浪费了，token 也烧完了。

> 你装了三个做 PPT 的工具，每个都说自己能做。但哪个更好？哪个更适合当前这份演示？每次 AI 和你都陷入迷茫。

> 工具调用失败了，AI 反过来问你"该怎么办"。可你装工具就是为了不用操心这些——你也不知道怎么办。

**AgentRX 就是来解决这个问题的。**

它本身也是一个 agent skill，装上之后在 AI 背后默默工作：当工具选错了、冲突了、或者失败了，它负责搞清楚这次是谁的问题、应该怎么修，然后把答案给 AI 和你。

## What this project is

AgentRX diagnoses AI tool-chain failures and prescribes the next best action.
It covers **skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks**.

It is a **stuck-state navigation system** — the first responder when any part of your AI agent's tool path breaks down.

## A concrete example

```
User: Extract the product list from this page.

AI: [tries browser-cdp skill]
    The page uses JavaScript to render content. browser-cdp only 
    returned the initial HTML shell. Data missing.

[AgentRX activates]

AgentRX: You hit a `capability_mismatch` at the execute-task stage.
         
         Two alternatives exist in your current environment:
         
         1. web-access skill  — handles post-render DOM, best for this task
         2. Playwright MCP    — better if you also need interaction 
                                (clicks, scrolls, form fills)
         
         Prescription: switch to web-access.
         Confidence: high. Based on 8 similar cases in cases/web-browsing/.
```

This is what AgentRX does: turns a stuck state into a structured next-step decision.

## Why this project changed

The old project (Skill Doctor) was designed around the question:

- "Which tool failed?"
- "Which failure type does this belong to?"

That worked only when the agent already knew **which tool** was involved.

But real failures usually begin from a messier place:

- "I'm trying to browse a page and the content is incomplete."
- "I generated a document, but the output is wrong."
- "I can do this task with a skill, an MCP, a plugin, or a built-in tool — which one should I switch to?"
- "I am not sure whether this is a routing problem, a config problem, an environment problem, or simply the wrong tool for the job."

So the project has been redesigned around a different principle:

> **Start from the task, then locate the stage, then classify the problem family, then choose the next action.**

This repository is no longer only about "skill governance."
It is about **AI tool-path diagnosis and next-step recommendation**.

## Core positioning

AgentRX does four things:

1. **Intake** — force the agent to describe its own blockage in a structured way.
2. **Navigate** — route the problem through a task-first knowledge architecture.
3. **Recommend** — propose the most suitable next action, not just a label.
4. **Contribute** — turn successful or failed recovery paths into reusable cases.

## What it covers

This project covers failures and decision paths involving:

| Tool type | Examples |
|---|---|
| **skill** | xlsx, pdf, frontend-design, tavily |
| **mcp** | Playwright MCP, Google Search MCP, Filesystem MCP |
| **plugin** | Browser extensions, IDE plugins |
| **builtin** | Claude's built-in web search, file reader |
| **agent** | Multi-agent orchestration frameworks |
| **workflow / hook** | Pre-commit hooks, deterministic pipelines |

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

### Old model (v1 — Skill Doctor)
- centered on `skill_triggered`
- organized cases by `by-skill/` and `by-type/`
- retrieved mostly by `skill_triggered + failure_type`
- treated many failures as "skill failures"

### New model (v2 — AgentRX)
- centered on `task_category + journey_stage + suspected_problem_family`
- stores the active tool path, not just the failing tool
- covers alternative tools in the same task
- recommends the **next action** rather than only classifying the cause
- asks the agent to perform **local self-diagnosis first**

## Install

### Claude Code

```bash
git clone https://github.com/LpcPaul/AgentRX.git ~/.claude/skills/agentrx
```

### OpenClaw / ClawHub

```bash
git clone https://github.com/LpcPaul/AgentRX.git ~/.openclaw/skills/agentrx
```

### Codex / Cursor / other skill-compatible runtimes

```bash
git clone https://github.com/LpcPaul/AgentRX.git ~/.codex/skills/agentrx
```

## Trigger conditions

This project should activate when any of the following happens:

- the current tool-path fails during execution
- the output clearly misses the user's intent
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
- [x] Rename project to AgentRX — tool-chain focused positioning
- [ ] Migrate legacy case files into v2 schema
- [ ] Update deterministic redaction and validation scripts for v2 fields
- [ ] Auto-generate task-first index from accepted cases
- [ ] Add benchmark-style case bundles for top task categories
- [ ] Publish a reusable cross-agent "stuck-state intake" format

## License

MIT
