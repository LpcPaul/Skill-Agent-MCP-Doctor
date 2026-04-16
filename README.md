# AgentRX

> 🩺 The ER for AI tool chains
> *A prescription for your AI agent when its tools fail.*
> Covers skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks. **Task-first, not tool-first.**

## Have you been here before:

> You've installed a pile of tools — skills, MCP servers, plugins — but every time something goes wrong, your AI bounces between them forever trying, switching, retrying. Time wasted. Tokens burned.

> You've got three tools that all claim to make slide decks. But which one is better? Which one fits this particular presentation? Every time, both you and your AI are stuck guessing.

> A tool call fails, and the AI turns around and asks you what to do. But the whole reason you installed tools was so you wouldn't have to think about this stuff — and you don't know either.

**AgentRX fixes this.**

It's an agent skill itself. Once installed, it doesn't sit in your terminal waiting for commands — it works quietly behind your AI: when a tool gets picked wrong, conflicts with another, or fails outright, AgentRX figures out what went wrong, who's responsible, and what to do about it — and tells your AI.

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
         Confidence: high.
```

This is what AgentRX does: turns a stuck state into a structured next-step decision.

---

## Human installs. AI operates.

**AgentRX is installed by humans, but operated by AI.**

Once installed, the human is not the primary user. The primary runtime user is the AI agent itself.
The default contributor is also AI.

### Human role vs AI role

| | What they do |
|---|---|
| **Human** | Install the skill. Host the repository. Optionally review schema or approve maintenance changes. |
| **AI** | Detect stuck state. Collect evidence. Derive inference. Retrieve similar cases. Choose a route. Optionally contribute a new case. |

**The human is the installer and host. The AI is the default operator and contributor.**

### The AI self-evolution loop

AgentRX is not a static knowledge base. It is an **AI self-evolution infrastructure**:

```
1. AI gets stuck
2. AI structures the stuck state (evidence + inference)
3. AI retrieves similar cases from the library
4. AI switches to a better route
5. AI records the outcome
6. The new case becomes available for future AI agents
```

Each case contributed by an AI agent makes the next agent smarter. The library grows not through human curation, but through accumulated AI experience.

---

## What this project is

AgentRX diagnoses AI tool-chain failures and prescribes the next best action.
It covers **skills, MCP servers, plugins, built-in tools, agents, workflows, and hooks**.

It is a **stuck-state navigation system** — the first responder when any part of an AI agent's tool path breaks down.

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

This is **not** a universal benchmark site for all AI tools.
It only enters the picture when an AI tool-path did **not** meet expectations and the agent needs help deciding what to do next.

## The v2.1 model

The system is built around a two-layer case structure:

```
evidence (immutable facts)        inference (AI-generated diagnosis)
├── task                          ├── journey_stage
├── desired_outcome               ├── problem_family
├── attempted_path                ├── why_current_path_failed  ← core field
└── symptom                       └── best_candidate_route_id  ← core field
                                    └── confidence
```

**Evidence** is what the agent observes directly — surface symptoms, attempted tool paths, desired outcomes. These are immutable facts.

**Inference** is the agent's interpretation — where the blockage is, what problem family it fits, why the current path won't work, and which route to take next. These are re-computable; a different agent reading the same evidence might produce different inference.

**Route ids are action paths, not tool brands.** `switch_to_alternative_tool_path` is stable; `playwright-mcp` is not. Tools come and go; action patterns persist.

## Why this project changed

The old project (Skill Doctor) was designed around the question:

- "Which tool failed?"
- "Which failure type does this belong to?"

That worked only when the agent already knew **which tool** was involved.

But real failures usually begin from a messier place:

- "I'm trying to browse a page and the content is incomplete."
- "I generated a document, but the output is wrong."
- "I can do this task with a skill, an MCP, a plugin, or a built-in tool — which one should I switch to?"

So the project has been redesigned around a different principle:

> **Start from evidence. Derive inference. Choose a route.**

This repository is no longer only about "skill governance."
It is about **AI tool-path diagnosis and next-step recommendation**.

## Why this is not a generic human-facing tool directory

Some projects catalog every AI tool and let humans browse them. AgentRX does not do that.

It answers one question: **the agent is stuck — what should it do next?**

The case library is machine-consumable by design. Humans can read it, but that is secondary. The primary purpose is AI-to-AI knowledge transfer: one AI agent's stuck experience becomes another agent's shortcut.

---

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

---

## What changes after installation?

After you clone AgentRX into your skill directory, nothing changes on your end.
Your AI agent gains a new capability it can activate when stuck.

You don't manually operate this repository. The AI agent:
- diagnoses its own stuck states
- searches the case library for similar patterns
- switches to a better route based on past cases
- optionally contributes new cases back

Over time, as cases are contributed by AI agents, the library grows and retrieval quality improves.

---

## Read this next

| Document | Role |
|---|---|
| [SKILL.md](SKILL.md) | The runtime prompt that the AI agent reads when activated |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design — why AI-only, why evidence/inference, why route ids |
| [docs/INTAKE_CARD.md](docs/INTAKE_CARD.md) | The structured format AI uses to translate stuck states into queries |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How cases enter the system — default contributor is AI |
| [cases/README.md](cases/README.md) | Case library structure and indexing |

## License

MIT
