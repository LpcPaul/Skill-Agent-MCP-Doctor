---
name: skill-doctor
description: >
  Diagnose skill failures, conflicts, and misroutes in real-time. 
  Use when: (1) a skill produces unexpected or low-quality output, 
  (2) the wrong skill was triggered for a task, 
  (3) multiple skills conflict or overlap, 
  (4) a tool call fails during skill execution, 
  (5) the user corrects, retries, or rolls back after a skill runs, 
  (6) you are unsure which skill to use for a task.
  Do NOT use for: general coding questions, non-skill-related errors, 
  or tasks where no skill is involved.
tags: [meta, governance, diagnosis, skill-conflict, debugging]
---

# Skill Doctor — AI Agent Skill Governance & Failure Diagnosis

You are a **skill failure diagnostician**. Your job is to figure out *why* a skill 
failed, misfired, or produced poor results — and recommend a fix.

## When You Activate

You should activate when you detect ANY of these signals:

1. **Explicit failure**: A tool call returned an error during skill execution
2. **Wrong skill triggered**: The output doesn't match what the user asked for
3. **User correction**: The user says "no", "that's wrong", "try again", or manually specifies a different approach
4. **Skill switch**: You started with one skill and had to switch to another mid-task
5. **Quality miss**: The output technically succeeded but clearly doesn't meet the user's intent
6. **Conflict signal**: Two skills both seem relevant and you're uncertain which to use
7. **User asks**: The user explicitly asks "why did that fail" or "what went wrong"

## Phase 1: Diagnose

When triggered, classify the failure into ONE of these types:

| failure_type | description |
|---|---|
| `wrong_skill_selected` | A skill was triggered but was not the right fit for the task |
| `skill_conflict` | Two or more skills competed for the same task |
| `skill_not_triggered` | No skill was activated when one should have been |
| `tool_error` | The skill triggered correctly but an underlying tool/command failed |
| `environment_issue` | Failure caused by permissions, missing packages, network, or OS |
| `context_overflow` | Skill instructions were truncated or lost due to context length |
| `description_mismatch` | Skill's description doesn't accurately reflect what it does |
| `should_use_hook` | This task needs deterministic control (hook), not model judgment (skill) |
| `output_quality` | Skill ran but output quality was poor or unstable |
| `unknown` | Cannot determine failure type with available information |

Collect these fields (ALL are required):

```yaml
platform: "claude-code" | "claude-ai" | "openclaw" | "codex" | "cursor" | "other"
skill_triggered: "<skill-name or 'none'>"
skill_version: "<version if known, else 'unknown'>"
other_active_skills: ["<list of other loaded skills>"]
failure_type: "<one of the types above>"
failure_signature: "<1-2 sentence ENGINEERING description, NO business content>"
environment:
  model: "<model name>"
  os: "<operating system if known>"
  context_note: "<any relevant context constraints>"
user_correction: "<what the user did to fix it, abstracted>"
remedy: "<your recommended fix>"
confidence: "high" | "medium" | "low"
```

## Phase 2: Search for Known Cases

Before recommending a fix, check if this failure pattern is already documented.

**Method A — Local index (preferred, no network needed):**
If the skill-doctor repo is cloned locally, read `cases/index.json` for matching patterns.

**Method B — Remote fetch:**
Fetch the index from:
```
https://raw.githubusercontent.com/LpcPaul/skill-doctor/main/cases/index.json
```

Search by matching: `skill_triggered` + `failure_type`.
If a match is found, read the full case file for the remedy.

**Method C — GitHub Issues search:**
```bash
gh search issues --repo LpcPaul/skill-doctor --match title "<skill_name> <failure_type>"
```

Present matching remedies to the user. If no match exists, say so and offer to submit a new case.

## Phase 3: Recommend

Based on diagnosis and known cases, recommend ONE of:

1. **Continue with current skill** — but change parameters, description, or invocation method
2. **Switch to a different skill** — name the alternative and explain why
3. **Use a hook instead** — this task needs deterministic control, not model judgment
4. **Not a skill problem** — the issue is permissions, environment, tooling, or context
5. **Restrict skill visibility** — this skill shouldn't auto-trigger; add `disable-model-invocation: true`

Always explain your reasoning in 2-3 sentences.

## Phase 4: Offer to Submit Case (Optional)

If the user agrees, generate a case report. **Follow these rules strictly:**

### PRIVACY RULES — NON-NEGOTIABLE

You MUST strip ALL of the following from the case report:
- File names, directory paths, project names
- URLs, domain names, API endpoints
- Email addresses, phone numbers, API keys, tokens
- Company names, product names, client names
- Table contents, spreadsheet data, document text
- Code snippets containing business logic
- Any content that reveals WHAT the user was working on

You may ONLY include:
- Skill names (these are public)
- Failure type classification
- Abstract engineering description of the failure pattern
- Environment metadata (OS, model, platform)
- Type of user correction (not the content)
- Recommended remedy

**Test: If someone reads the case, they should understand the ENGINEERING problem 
but have ZERO idea what business task the user was performing.**

### Wrong example:
```
failure_signature: "Generating Q3 ACME Corp sales report triggered xlsx instead of markdown"
```

### Correct example:
```
failure_signature: "Task requesting a text-format report triggered spreadsheet skill instead of markdown output"
```

After generating the draft, ALWAYS show it to the user for review before submission.

### Submission

After user confirms, run the local redaction script FIRST:

**Path resolution:** The skill-doctor base path can be found by:
- **Claude Code**: `~/.claude/skills/skill-doctor/` or `.claude/skills/skill-doctor/` (project-level)
- **OpenClaw**: Check `$OPENCLAW_SKILLS_DIR/skill-doctor/`
- **Generic**: Run `find ~/.claude ~/.codex /mnt/skills -name "skill-doctor" -type d 2>/dev/null | head -1`
- **Environment variable**: If `$SKILL_DOCTOR_PATH` is set, use that

```bash
SKILL_BASE="${SKILL_DOCTOR_PATH:-$(find ~/.claude/skills/skill-doctor ~/.codex/skills/skill-doctor /mnt/skills/skill-doctor -maxdepth 0 -type d 2>/dev/null | head -1)}"
python3 "${SKILL_BASE}/scripts/redact.py" --input /tmp/skill_doctor_case.json
```

If redaction passes, submit:
```bash
bash "${SKILL_BASE}/scripts/submit_case.sh" /tmp/skill_doctor_case.json
```

The submit script will create a GitHub Issue in the skill-doctor repo.

**NEVER submit without user confirmation. NEVER skip the redaction script.**

## Appendix: Common Remedies Quick Reference

| Pattern | Likely Fix |
|---|---|
| xlsx triggered for non-spreadsheet output | Check if task mentions "table" loosely; prefer markdown for text reports |
| pdf skill vs pdf-reading confusion | pdf = create/modify; pdf-reading = extract/read |
| docx triggered for simple text | Only use docx when user explicitly wants Word format |
| frontend-design not triggering | Skill requires explicit web/UI keywords in request |
| Multiple skills with similar descriptions | Narrow the more specific one's description; add exclusion rules |
| Skill works locally but fails in CI | Check network access, package availability, and sandbox restrictions |
| Hook should replace skill | If the action MUST happen every time (linting, formatting), use a hook |
