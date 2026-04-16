# AgentRX

> 🩺 A task-first stuck-state protocol + deterministic retrieval layer for AI agents.
> When your agent's tool path fails, AgentRX structures the failure, retrieves similar cases, and surfaces candidate routes.

## What is AgentRX?

AgentRX is **not** a human-facing tool directory. It is a **machine-consumable protocol** that answers one question:

> **The agent is stuck — what should it do next?**

It provides:

- **Schema** — a standard v2.1 case format (evidence + inference separation)
- **Route registry** — stable action paths, not tool brand names
- **Validation** — JSON Schema + cross-file rule consistency checks
- **Indexing** — lightweight case library index for retrieval
- **Deterministic retrieval** — `retrieve_cases.py` finds top-k candidate cases

AgentRX does **not** run inference for the agent. Route recommendation is the agent's own reasoning, based on retrieved cases + the route registry.

## A concrete example

```
User: Extract the product list from this page.

AI: [tries browser-cdp skill]
    The page uses JavaScript to render content. browser-cdp only
    returned the initial HTML shell. Data missing.

[AgentRX activates]

AgentRX: Retrieved similar cases → route: switch_to_alternative_tool_path

         Why: current tool captures static HTML only; page requires
         JavaScript rendering.

         Candidate: playwright-mcp can render the page and extract
         the full DOM. web_fetch is a lighter option for static pages.
```

---

## What AgentRX provides today

| Component | Status |
|---|---|
| Case schema (v2.1) | ✅ |
| Route registry | ✅ |
| Case validation | ✅ (JSON Schema + cross-file rules) |
| Index building | ✅ |
| Deterministic retrieval | ✅ (`retrieve_cases.py`) |
| Case ID generation | ✅ (`new_case_id.py`) |

## What AgentRX does **not** provide (yet)

| Component | Status |
|---|---|
| Automated case review / merge / publish pipeline | 🚧 planned |
| Python-based route recommender | ❌ out of scope — agent does its own route inference |

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

## How it works

```
1. AI gets stuck (concrete failure signal)
2. AI structures the stuck state (evidence + inference)
3. AI retrieves similar cases via retrieve_cases.py
4. AI chooses a route based on retrieved cases + rules/routes.yaml
5. AI records the outcome
6. The new case becomes available for future AI agents
```

### Human installs. AI operates.

| | What they do |
|---|---|
| **Human** | Install the skill. Host the repository. Maintain schema/taxonomy. |
| **AI** | Detect stuck state. Collect evidence. Retrieve similar cases. Choose a route. Optionally contribute a new case. |

**AI contributors must submit complete v2.1 JSON.** Human fallback / form-to-JSON assembly is no longer supported.

---

## Read this next

| Document | Role |
|---|---|
| [SKILL.md](SKILL.md) | The runtime protocol the AI agent reads when activated |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design — why evidence/inference, why route ids |
| [docs/INTAKE_CARD.md](docs/INTAKE_CARD.md) | The structured intake card format |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How cases enter the system — JSON-only contribution path |
| [cases/README.md](cases/README.md) | Case library structure and indexing |

## License

MIT
