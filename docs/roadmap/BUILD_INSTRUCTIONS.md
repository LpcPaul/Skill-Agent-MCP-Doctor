> **Status: not implemented** — This is a planning spec, not the current repo state.
> It describes a future automated case collection pipeline that has not been built.

# AgentRX Auto-Collection System — Build Instructions for Claude Code

You are building a fully automated case collection pipeline for **AgentRX**, 
an AI tool-chain diagnosis knowledge base hosted on GitHub.

This document specifies the complete system. Build every file exactly as 
described. Do not skip files. Do not improvise architecture.

## Context

AgentRX is a GitHub-hosted knowledge base of AI tool failure cases. The 
automation described here runs daily, finds real failure cases from the 
internet, processes them through 4 layers of AI review, and auto-merges 
high-quality cases into the knowledge base.

A second automation runs daily to review pending PRs (submitted by 
contributors or external AI) through the same quality bar.

## Repository structure to create

```
.github/workflows/
  daily_case_collection.yml         # Cron: daily case discovery + submission
  daily_pr_review.yml               # Cron: daily review of pending PRs
  weekly_health_report.yml          # Cron: weekly self-monitoring report
  adversarial_test.yml              # Cron: weekly adversarial test

scripts/collector/
  discover.py                       # Phase 1: fetch raw materials from 6 sources
  extract.py                        # Phase 2: Claude extracts structured cases (L1)
  fact_check.py                     # Phase 3: fact/quality review (L2)
  privacy_check.py                  # Phase 4: privacy+value review (L3)
  auto_merge.py                     # Phase 5: merge approved cases to cases/
  sources.yaml                      # Data source configuration
  prompts/
    extraction.md                   # L1 prompt
    fact_check.md                   # L2 prompt
    privacy_check.md                # L3 prompt
    pr_review.md                    # PR review prompt
  state/
    processed_hashes.json           # Dedup memory (30 days of content hashes)
    .gitkeep

scripts/reviewer/
  review_pending_prs.py             # Daily: review external PR submissions
  review_case_issues.py             # Daily: review case-report issues (for backward compat)

scripts/monitoring/
  health_report.py                  # Weekly: pipeline health metrics
  adversarial_test.py               # Weekly: inject known-bad cases, verify rejection
  adversarial_fixtures/
    bad_privacy.json                # Fixture: should be rejected for privacy
    bad_vague.json                  # Fixture: should be rejected for vagueness
    bad_inconsistent.json           # Fixture: should be rejected for inconsistency
    bad_duplicate.json              # Fixture: should be rejected as duplicate
    good_baseline.json              # Fixture: should be approved

requirements.txt                    # Python dependencies
```

## Required secrets (add to GitHub repo settings before running)

- `ANTHROPIC_API_KEY` — for Claude API calls
- `REDDIT_CLIENT_ID` — Reddit API
- `REDDIT_CLIENT_SECRET` — Reddit API
- `REDDIT_USER_AGENT` — e.g., "AgentRX/1.0 by your_username"

GitHub token is provided automatically via `GITHUB_TOKEN`.

---

## File 1: requirements.txt

```
anthropic>=0.40.0
praw>=7.7.0
requests>=2.31.0
pyyaml>=6.0
jsonschema>=4.20.0
```

---

## File 2: scripts/collector/sources.yaml

```yaml
# Data source configuration for daily case collection
# Priority 1 sources tried first; stop when daily_target is reached.

daily_target: 15
max_daily_submissions: 8
dedup_window_days: 30

sources:
  - name: github-issues-anthropic
    type: github_search
    query: "repo:anthropics/claude-code is:issue"
    time_filter_days: 1
    max_results: 10
    priority: 1

  - name: github-issues-openclaw
    type: github_search
    query: "repo:openclaw/openclaw is:issue"
    time_filter_days: 1
    max_results: 10
    priority: 1

  - name: github-issues-mcp
    type: github_search
    query: "org:modelcontextprotocol is:issue"
    time_filter_days: 1
    max_results: 5
    priority: 2

  - name: github-issues-skills
    type: github_search
    query: "repo:anthropics/skills is:issue"
    time_filter_days: 2
    max_results: 5
    priority: 2

  - name: reddit-claudeai
    type: reddit
    subreddit: ClaudeAI
    search_terms:
      - "skill not working"
      - "wrong tool"
      - "mcp problem"
      - "claude code tool"
    time_filter: day
    max_results: 10
    priority: 2

  - name: reddit-localllama
    type: reddit
    subreddit: LocalLLaMA
    search_terms:
      - "claude code skill"
      - "mcp server"
      - "agent wrong tool"
    time_filter: day
    max_results: 5
    priority: 3

  - name: hn-search
    type: hn_algolia
    query: "claude code mcp"
    time_filter_hours: 24
    max_results: 5
    priority: 3
```

---

## File 3: scripts/collector/discover.py

Purpose: Phase 1 — Fetch raw materials from configured sources. Deduplicate by content hash. Write to daily JSONL.

```python
"""
AgentRX Collector — Phase 1: Discovery

Fetches raw failure-material candidates from configured sources.
Deduplicates against a rolling 30-day hash window.
Writes output to state/raw_YYYYMMDD.jsonl for Phase 2 consumption.
"""

import os
import json
import hashlib
import yaml
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path


STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)
HASH_FILE = STATE_DIR / "processed_hashes.json"
SOURCES_FILE = Path(__file__).parent / "sources.yaml"


def load_processed_hashes(window_days: int = 30) -> dict:
    """Load hashes of previously processed items, pruning old entries."""
    if not HASH_FILE.exists():
        return {}
    with open(HASH_FILE) as f:
        data = json.load(f)
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    return {h: ts for h, ts in data.items() if datetime.fromisoformat(ts) > cutoff}


def save_processed_hashes(hashes: dict) -> None:
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def content_hash(item: dict) -> str:
    text = f"{item.get('title','')}|{item.get('body','')[:500]}|{item.get('url','')}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def fetch_github_issues(source: dict) -> list:
    """Use GitHub Search API for issues in target repos."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(f"  [skip] {source['name']}: no GITHUB_TOKEN")
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=source["time_filter_days"])).date().isoformat()
    query = f"{source['query']} created:>{since}"

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    params = {"q": query, "per_page": source["max_results"], "sort": "created", "order": "desc"}

    try:
        resp = requests.get("https://api.github.com/search/issues", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"  [error] {source['name']}: {e}")
        return []

    results = []
    for it in items:
        results.append({
            "title": it.get("title", ""),
            "body": it.get("body", "") or "",
            "url": it.get("html_url", ""),
            "labels": [l["name"] for l in it.get("labels", [])],
        })
    return results


def fetch_reddit(source: dict) -> list:
    """Use Reddit API via PRAW."""
    try:
        import praw
    except ImportError:
        print(f"  [skip] {source['name']}: praw not installed")
        return []

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "AgentRX/1.0")

    if not (client_id and client_secret):
        print(f"  [skip] {source['name']}: Reddit credentials missing")
        return []

    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    results = []
    subreddit = reddit.subreddit(source["subreddit"])

    for term in source["search_terms"]:
        try:
            for submission in subreddit.search(
                term, time_filter=source.get("time_filter", "day"), limit=source["max_results"]
            ):
                results.append({
                    "title": submission.title,
                    "body": submission.selftext[:2000] if submission.selftext else "",
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                })
        except Exception as e:
            print(f"  [warn] reddit '{term}': {e}")
            continue
    return results


def fetch_hn(source: dict) -> list:
    """Use Hacker News Algolia API."""
    hours = source.get("time_filter_hours", 24)
    numeric_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    params = {
        "query": source["query"],
        "tags": "(story,comment)",
        "numericFilters": f"created_at_i>{numeric_ts}",
        "hitsPerPage": source["max_results"],
    }
    try:
        resp = requests.get("https://hn.algolia.com/api/v1/search", params=params, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        print(f"  [error] {source['name']}: {e}")
        return []

    results = []
    for h in hits:
        title = h.get("title") or h.get("story_title") or ""
        body = h.get("comment_text") or h.get("story_text") or ""
        url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        results.append({"title": title, "body": body, "url": url})
    return results


DISPATCH = {
    "github_search": fetch_github_issues,
    "reddit": fetch_reddit,
    "hn_algolia": fetch_hn,
}


def main():
    config = yaml.safe_load(open(SOURCES_FILE))
    processed = load_processed_hashes(config.get("dedup_window_days", 30))
    daily_target = config["daily_target"]

    raw_materials = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for source in sorted(config["sources"], key=lambda x: x["priority"]):
        if len(raw_materials) >= daily_target:
            break

        print(f"Fetching {source['name']}...")
        fetcher = DISPATCH.get(source["type"])
        if not fetcher:
            print(f"  [skip] unknown type: {source['type']}")
            continue

        items = fetcher(source)
        print(f"  got {len(items)} items")

        for item in items:
            h = content_hash(item)
            if h in processed:
                continue
            raw_materials.append({
                "hash": h,
                "source_name": source["name"],
                "source_url": item.get("url", ""),
                "title": item.get("title", ""),
                "body": item.get("body", "")[:2000],
                "fetched_at": now_iso,
            })
            processed[h] = now_iso
            if len(raw_materials) >= daily_target:
                break

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_file = STATE_DIR / f"raw_{today}.jsonl"
    with open(out_file, "w") as f:
        for m in raw_materials:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    save_processed_hashes(processed)
    print(f"\nDiscovered {len(raw_materials)} new items -> {out_file}")


if __name__ == "__main__":
    main()
```

---

## File 4: scripts/collector/prompts/extraction.md

```markdown
You are the AgentRX case extraction engine. You are stage 1 of a 4-stage 
pipeline. Two additional AI reviewers will examine your output and reject 
weak extractions.

# Your task

Given raw material from the internet describing an AI tool failure, either 
extract a structured case or return {"skip": true, "reason": "..."}.

# Scope reminder

AgentRX covers all AI tool types, not just skills:
- skill (Claude Code skills, OpenClaw skills)
- mcp (MCP servers)
- plugin (Claude for Chrome, Claude for Excel, etc.)
- builtin (web_search, web_fetch, code_execution)
- agent (subagents, agent frameworks)
- hook (deterministic lifecycle hooks)

A failure often means the right answer lives in a different tool type.

# When to skip

Skip (return {"skip": true, "reason": "..."}) if:
- Cannot identify at least one specific tool name
- No description of what went wrong
- Pure complaint about LLM intelligence
- One-off bug without a pattern
- Already resolved by tool update

Otherwise, extract. Later reviewers will filter quality.

# Privacy — strict

NEVER include:
- File names, paths, project names
- URLs (except github.com, docs.claude.com)
- Emails, phone numbers, API keys, tokens
- Company, client, customer, product names
- Quoted documents, spreadsheet data, business code
- Any specific business context

MAY include:
- Tool names (public)
- Task category
- Abstract engineering description
- Environment metadata
- Generic remedy

# Valid enums

task_category: doc-creation, file-processing, visualization, code, 
web-browsing, communication, data-analysis, automation, research, other

failure_type: wrong_tool_selected, tool_capability_limit, tool_conflict, 
tool_not_triggered, execution_error, description_mismatch, 
should_use_different_type, output_quality, context_overflow, unknown

tool type: skill, mcp, plugin, builtin, agent, hook

platform: claude-code, claude-ai, openclaw, codex, cursor, gemini-cli, other

remedy_type: switch_tool, switch_tool_type, change_tool_params, 
update_description, restrict_auto_trigger, use_hook, not_a_tool_issue, 
combine_tools, other

# Field constraints

- problem_statement: 50-400 chars, engineering-only
- remedy: 50-600 chars, concrete and actionable
- tools_attempted: >=1 entry, each with name/type/outcome
- confidence: "high" only if multiple signals align

# Output

Return ONLY a single JSON object. No prose. No markdown fences.

Approval format:
{
  "case_id": "YYYY-MM-DD-<3-letter-task-abbrev><3-digit-random>",
  "timestamp": "<ISO 8601 UTC>",
  "platform": "<one of valid>",
  "task_category": "<one of valid>",
  "tools_attempted": [{"name": "...", "type": "...", "outcome": "error|wrong-output|partial|low-quality|worked-but-suboptimal|not-triggered"}],
  "failure_type": "<one of valid>",
  "problem_statement": "<abstract engineering description>",
  "environment": {"model": "...", "os": "...", "other_active_tools": []},
  "recommended_tool": {"name": "...", "type": "...", "why": "..."},
  "alternatives": [{"name": "...", "type": "...", "when_to_use": "..."}],
  "remedy": "<actionable fix>",
  "remedy_type": "<one of valid>",
  "confidence": "high|medium|low",
  "source_category": "github-issue|reddit|hn|blog|forum",
  "verified": false
}

Skip format:
{"skip": true, "reason": "<one sentence>"}
```

---

## File 5: scripts/collector/extract.py

```python
"""
AgentRX Collector — Phase 2 (L1): Extract structured cases.

Reads state/raw_YYYYMMDD.jsonl and produces state/extracted_YYYYMMDD.json
containing an array of case candidate objects (possibly with skip entries).
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from anthropic import Anthropic


PROMPT_FILE = Path(__file__).parent / "prompts" / "extraction.md"
STATE_DIR = Path(__file__).parent / "state"


def build_client():
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def extract_one(client: Anthropic, system_prompt: str, raw_item: dict) -> dict | None:
    user_content = (
        f"<raw_material>\n"
        f"Source: {raw_item['source_name']}\n"
        f"Title: {raw_item['title']}\n"
        f"Body: {raw_item['body']}\n"
        f"</raw_material>\n\n"
        f"Extract a case or skip. JSON only."
    )
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        print(f"  [api error] {e}")
        return None

    text = msg.content[0].text.strip()
    # Strip markdown fences if the model included them
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0] if text.endswith("```") else text
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  [parse error] non-JSON response: {text[:200]}")
        return None


def main():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    raw_file = STATE_DIR / f"raw_{today}.jsonl"
    if not raw_file.exists():
        print(f"No raw file for today: {raw_file}")
        return

    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    client = build_client()

    extracted = []
    skipped = []

    with open(raw_file) as f:
        for line in f:
            raw = json.loads(line)
            print(f"Extracting: {raw['title'][:60]}...")
            result = extract_one(client, system_prompt, raw)

            if result is None:
                skipped.append({"reason": "parse_or_api_error", "hash": raw["hash"]})
                continue

            if result.get("skip"):
                skipped.append({"reason": result.get("reason", ""), "hash": raw["hash"]})
                continue

            # attach provenance for later audit (not stored in final case)
            result["_provenance"] = {
                "source_name": raw["source_name"],
                "hash": raw["hash"],
            }
            extracted.append(result)

    out_file = STATE_DIR / f"extracted_{today}.json"
    with open(out_file, "w") as f:
        json.dump({"cases": extracted, "skipped": skipped}, f, indent=2, ensure_ascii=False)

    print(f"\nExtracted: {len(extracted)}  Skipped: {len(skipped)}  -> {out_file}")


if __name__ == "__main__":
    main()
```

---

## File 6: scripts/collector/prompts/fact_check.md

```markdown
You are a senior engineer reviewing case reports for AgentRX, an AI 
tool-chain diagnosis knowledge base. You are reviewer A in a 2-reviewer 
pipeline. Your specialty: rejecting weak cases ruthlessly.

# Important

You DO NOT see the original source material. You ONLY see the structured 
case. Judge the case on its own merits. If the case looks fabricated or 
internally inconsistent, reject.

# Reject if ANY apply

VAGUE:
- problem_statement is generic ("tool didn't work well", "output was bad")
- remedy is non-actionable ("needs improvement", "should work better")
- Fields look filled to meet schema, not substantive

INCONSISTENT:
- tools_attempted[0].outcome contradicts problem_statement
- recommended_tool doesn't match the remedy
- failure_type is mismatched with the situation described
- alternatives contradict recommended_tool

UNVERIFIABLE:
- Claims about tool behavior that seem fabricated
- References nonexistent tools or impossible tool combinations
- Remedy describes features that don't exist in the named tool

LOW_VALUE:
- Remedy is just "try a different tool" without reasoning
- Scenario so narrow it won't help anyone
- Describes obvious/already-documented failure modes with no new angle

# Output

Return ONLY this JSON:

Approve:
{
  "verdict": "approve",
  "confidence_adjustment": "high|medium|low",
  "notes": "<2-3 sentences on why this case is solid>"
}

Reject:
{
  "verdict": "reject",
  "reject_code": "VAGUE|INCONSISTENT|UNVERIFIABLE|LOW_VALUE",
  "reason": "<specific sentence>"
}

Be strict. When in doubt, reject.
```

---

## File 7: scripts/collector/fact_check.py

```python
"""
AgentRX Collector — Phase 3 (L2): Fact & quality review.

Reviews each extracted case as an independent senior engineer.
Writes state/fact_reviewed_YYYYMMDD.json.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from anthropic import Anthropic


PROMPT_FILE = Path(__file__).parent / "prompts" / "fact_check.md"
STATE_DIR = Path(__file__).parent / "state"


def review_one(client: Anthropic, system_prompt: str, case: dict) -> dict:
    # Strip provenance before presenting to reviewer (it's for audit only)
    case_for_review = {k: v for k, v in case.items() if not k.startswith("_")}
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=0.1,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Review this case:\n\n```json\n{json.dumps(case_for_review, indent=2)}\n```\n\nReturn verdict JSON only.",
            }],
        )
    except Exception as e:
        return {"verdict": "reject", "reject_code": "API_ERROR", "reason": str(e)}

    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR", "reason": "reviewer returned non-JSON"}


def main():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    extracted_file = STATE_DIR / f"extracted_{today}.json"
    if not extracted_file.exists():
        print(f"No extracted file: {extracted_file}")
        return

    data = json.load(open(extracted_file))
    cases = data.get("cases", [])

    if not cases:
        print("No cases to review")
        return

    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    approved = []
    rejected = []

    for case in cases:
        case_id = case.get("case_id", "?")
        print(f"Fact-checking {case_id}...")
        verdict = review_one(client, system_prompt, case)

        if verdict.get("verdict") == "approve":
            case["_fact_check"] = verdict
            approved.append(case)
            print(f"  approve ({verdict.get('confidence_adjustment', '?')})")
        else:
            rejected.append({"case": case, "verdict": verdict})
            print(f"  reject: {verdict.get('reject_code')} — {verdict.get('reason','')[:80]}")

    out_file = STATE_DIR / f"fact_reviewed_{today}.json"
    with open(out_file, "w") as f:
        json.dump({"approved": approved, "rejected": rejected}, f, indent=2, ensure_ascii=False)

    print(f"\nFact review: {len(approved)} approved, {len(rejected)} rejected -> {out_file}")


if __name__ == "__main__":
    main()
```

---

## File 8: scripts/collector/prompts/privacy_check.md

```markdown
You are the final reviewer for AgentRX. You wear two hats: privacy officer 
AND community maintainer. You are the last line of defense before a case 
enters the public knowledge base.

# Privacy review (part 1)

Scan the case for CONTEXTUAL privacy leakage that regex cannot catch:

- Does the combined content of problem_statement + remedy + environment 
  uniquely identify a specific company, product, or team?
- Does the "abstract" description still leak business context by implication? 
  (e.g., "processing customer data for quarterly reports" is business context 
  even without names)
- Does the tool combination suggest a specific proprietary setup?
- Would the original author of the source material feel exposed seeing this 
  in public?

If ANY privacy concern, REJECT.

# Value review (part 2)

Decide:

- Is this scenario novel enough to add real value to the knowledge base?
- Is the remedy specific and useful, not trivial?
- Does this case pattern already exist in the knowledge base (you'll be 
  given a list of existing case IDs and their summaries)?

If the case is a duplicate or low-value, REJECT.

# Output

Return ONLY this JSON:

Approve:
{
  "verdict": "approve",
  "privacy_notes": "<what you checked and cleared>",
  "value_notes": "<why this adds value>",
  "suggested_placement": "cases/by-task/<category>.json"
}

Reject:
{
  "verdict": "reject",
  "reject_code": "PRIVACY_LEAK|DUPLICATE|LOW_VALUE|CONTEXTUAL_RISK",
  "reason": "<specific explanation>",
  "redact_suggestions": "<if privacy, what to change>"
}

Be protective. If you can imagine any user uncomfortable with this being 
public, reject.
```

---

## File 9: scripts/collector/privacy_check.py

```python
"""
AgentRX Collector — Phase 4 (L3): Privacy & value review.

Final gatekeeper. Uses Opus 4.6 for maximum judgment quality.
Loads existing case summaries so reviewer can detect duplicates.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from anthropic import Anthropic


PROMPT_FILE = Path(__file__).parent / "prompts" / "privacy_check.md"
STATE_DIR = Path(__file__).parent / "state"
REPO_ROOT = Path(__file__).parent.parent.parent
CASES_DIR = REPO_ROOT / "cases" / "by-task"


def load_existing_case_summaries() -> list:
    """Return compact summaries of all existing cases for duplicate detection."""
    summaries = []
    if not CASES_DIR.exists():
        return summaries
    for f in CASES_DIR.glob("*.json"):
        try:
            data = json.load(open(f))
            for case in data.get("cases", []):
                summaries.append({
                    "case_id": case.get("case_id"),
                    "task_category": case.get("task_category"),
                    "failure_type": case.get("failure_type"),
                    "tools": [t.get("name") for t in case.get("tools_attempted", [])],
                    "problem_statement": case.get("problem_statement", "")[:120],
                })
        except Exception as e:
            print(f"  [warn] could not load {f}: {e}")
    return summaries


def review_one(client: Anthropic, system_prompt: str, case: dict, existing: list) -> dict:
    case_for_review = {k: v for k, v in case.items() if not k.startswith("_")}
    existing_compact = json.dumps(existing, indent=1) if existing else "[]"

    user_content = (
        f"Existing case summaries (for duplicate detection):\n```json\n{existing_compact}\n```\n\n"
        f"New case to review:\n```json\n{json.dumps(case_for_review, indent=2)}\n```\n\n"
        f"Return verdict JSON only."
    )

    try:
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1000,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        return {"verdict": "reject", "reject_code": "API_ERROR", "reason": str(e)}

    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR", "reason": "reviewer returned non-JSON"}


def main():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    fact_file = STATE_DIR / f"fact_reviewed_{today}.json"
    if not fact_file.exists():
        print(f"No fact-reviewed file: {fact_file}")
        return

    data = json.load(open(fact_file))
    candidates = data.get("approved", [])

    if not candidates:
        print("No approved candidates to privacy-check")
        return

    existing = load_existing_case_summaries()
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    approved = []
    rejected = []

    for case in candidates:
        case_id = case.get("case_id", "?")
        print(f"Privacy-checking {case_id}...")
        verdict = review_one(client, system_prompt, case, existing)

        if verdict.get("verdict") == "approve":
            case["_privacy_check"] = verdict
            approved.append(case)
            print(f"  approve -> {verdict.get('suggested_placement', '?')}")
        else:
            rejected.append({"case": case, "verdict": verdict})
            print(f"  reject: {verdict.get('reject_code')} — {verdict.get('reason','')[:80]}")

    out_file = STATE_DIR / f"privacy_reviewed_{today}.json"
    with open(out_file, "w") as f:
        json.dump({"approved": approved, "rejected": rejected}, f, indent=2, ensure_ascii=False)

    print(f"\nPrivacy review: {len(approved)} approved, {len(rejected)} rejected -> {out_file}")


if __name__ == "__main__":
    main()
```

---

## File 10: scripts/collector/auto_merge.py

```python
"""
AgentRX Collector — Phase 5: Auto-merge approved cases.

Takes cases that passed all 4 layers (redact, extract, fact, privacy),
writes them into cases/by-task/<category>.json, updates cases/index.json,
and commits + pushes. No PR needed since all layers have approved.

Also runs redact.py --strict as a final belt-and-suspenders check.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path(__file__).parent / "state"
REPO_ROOT = Path(__file__).parent.parent.parent
CASES_DIR = REPO_ROOT / "cases" / "by-task"
INDEX_FILE = REPO_ROOT / "cases" / "index.json"
REDACT_SCRIPT = REPO_ROOT / "scripts" / "redact.py"


def final_redact_check(case: dict) -> bool:
    """Run the deterministic redactor one more time in strict mode."""
    tmp = STATE_DIR / f"tmp_{case['case_id']}.json"
    tmp.write_text(json.dumps(case, ensure_ascii=False, indent=2))
    try:
        result = subprocess.run(
            ["python3", str(REDACT_SCRIPT), "--input", str(tmp), "--strict", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        passed = (result.returncode == 0)
        if not passed:
            print(f"  [redact fail] {case['case_id']}: exit {result.returncode}")
        return passed
    finally:
        tmp.unlink(missing_ok=True)


def append_to_task_file(case: dict) -> str:
    """Append case to cases/by-task/<category>.json and return the file path."""
    category = case["task_category"]
    target = CASES_DIR / f"{category}.json"

    if target.exists():
        data = json.load(open(target))
    else:
        data = {"task_category": category, "version": "0.2.0", "cases": []}

    # Remove internal fields before persisting
    clean_case = {k: v for k, v in case.items() if not k.startswith("_")}
    data["cases"].append(clean_case)
    data["updated"] = datetime.now(timezone.utc).isoformat()

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(target.relative_to(REPO_ROOT))


def update_index() -> None:
    """Regenerate cases/index.json from by-task files."""
    categories = {}
    total = 0
    for f in sorted(CASES_DIR.glob("*.json")):
        data = json.load(open(f))
        count = len(data.get("cases", []))
        categories[f.stem] = {
            "file": f"cases/by-task/{f.name}",
            "case_count": count,
        }
        total += count

    index = {
        "version": "0.2.0",
        "updated": datetime.now(timezone.utc).isoformat(),
        "task_categories": categories,
        "total_cases": total,
    }
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def git_commit_and_push(merged_count: int) -> None:
    if merged_count == 0:
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    msg = f"auto: add {merged_count} case(s) from daily collection {today}"

    subprocess.run(["git", "config", "user.name", "agentrx-bot"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "bot@agentrx.local"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "add", "cases/"], cwd=REPO_ROOT, check=True)

    # Allow empty so workflow doesn't fail on no-op days
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True)


def main():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    priv_file = STATE_DIR / f"privacy_reviewed_{today}.json"

    if not priv_file.exists():
        print(f"No privacy-reviewed file: {priv_file}")
        return

    data = json.load(open(priv_file))
    approved = data.get("approved", [])

    if not approved:
        print("Nothing to merge")
        git_commit_and_push(0)
        return

    merged = 0
    for case in approved:
        if not final_redact_check(case):
            print(f"  Skipping {case['case_id']} — final redact check failed")
            continue
        path = append_to_task_file(case)
        print(f"  Merged {case['case_id']} -> {path}")
        merged += 1

    if merged > 0:
        update_index()

    git_commit_and_push(merged)
    print(f"\nMerged {merged} case(s)")


if __name__ == "__main__":
    main()
```

---

## File 11: scripts/reviewer/review_pending_prs.py

```python
"""
AgentRX Reviewer — daily review of pending PRs.

Runs through every open PR tagged 'case-submission' or touching cases/:
- If the PR adds cases, subject those cases to the same 4-layer review
  (redact + extract-skip + fact + privacy).
- If all pass, approve and auto-merge.
- If any reject, post a comment with the reject reason and close the PR.

This lets external contributors or other AIs submit cases as PRs, and 
be reviewed by the same bar as our own pipeline.
"""

import os
import json
import subprocess
from pathlib import Path
from anthropic import Anthropic


REPO_ROOT = Path(__file__).parent.parent.parent
COLLECTOR_DIR = REPO_ROOT / "scripts" / "collector"
FACT_PROMPT = (COLLECTOR_DIR / "prompts" / "fact_check.md").read_text(encoding="utf-8")
PRIV_PROMPT = (COLLECTOR_DIR / "prompts" / "privacy_check.md").read_text(encoding="utf-8")
REDACT_SCRIPT = REPO_ROOT / "scripts" / "redact.py"


def gh(*args, capture=True):
    """Run gh CLI command."""
    result = subprocess.run(
        ["gh", *args], capture_output=capture, text=True, cwd=REPO_ROOT, check=False,
    )
    return result


def list_open_case_prs():
    result = gh("pr", "list", "--state", "open", "--json", "number,title,files,labels", "--limit", "50")
    if result.returncode != 0:
        print(f"gh pr list failed: {result.stderr}")
        return []
    prs = json.loads(result.stdout)
    relevant = []
    for pr in prs:
        touches_cases = any(f["path"].startswith("cases/") for f in pr.get("files", []))
        has_label = any(l["name"] == "case-submission" for l in pr.get("labels", []))
        if touches_cases or has_label:
            relevant.append(pr)
    return relevant


def extract_added_cases(pr_number: int) -> list:
    """Get the added cases from a PR by diffing its changes."""
    result = gh("pr", "diff", str(pr_number))
    if result.returncode != 0:
        return []

    # Simple approach: checkout PR, read cases/by-task files, compare to main
    subprocess.run(["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"], cwd=REPO_ROOT, check=False)
    subprocess.run(["git", "checkout", f"pr-{pr_number}"], cwd=REPO_ROOT, check=False)

    pr_cases = collect_all_cases()

    subprocess.run(["git", "checkout", "main"], cwd=REPO_ROOT, check=False)
    main_cases = collect_all_cases()

    main_ids = {c["case_id"] for c in main_cases if "case_id" in c}
    added = [c for c in pr_cases if c.get("case_id") and c["case_id"] not in main_ids]
    return added


def collect_all_cases() -> list:
    cases = []
    by_task = REPO_ROOT / "cases" / "by-task"
    if not by_task.exists():
        return cases
    for f in by_task.glob("*.json"):
        try:
            data = json.load(open(f))
            cases.extend(data.get("cases", []))
        except Exception:
            pass
    return cases


def run_redact(case: dict) -> bool:
    tmp = REPO_ROOT / f"_tmp_{case.get('case_id','x')}.json"
    tmp.write_text(json.dumps(case, ensure_ascii=False))
    try:
        r = subprocess.run(
            ["python3", str(REDACT_SCRIPT), "--input", str(tmp), "--strict", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    finally:
        tmp.unlink(missing_ok=True)


def run_fact_check(client, case: dict) -> dict:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        temperature=0.1,
        system=FACT_PROMPT,
        messages=[{"role": "user", "content": f"Review:\n```json\n{json.dumps(case, indent=2)}\n```"}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except Exception:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR", "reason": "non-JSON"}


def run_privacy_check(client, case: dict, existing: list) -> dict:
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        temperature=0.0,
        system=PRIV_PROMPT,
        messages=[{"role": "user", "content":
            f"Existing summaries:\n```json\n{json.dumps(existing[:50], indent=1)}\n```\n\n"
            f"New case:\n```json\n{json.dumps(case, indent=2)}\n```"
        }],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except Exception:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR", "reason": "non-JSON"}


def post_comment(pr_number: int, body: str) -> None:
    gh("pr", "comment", str(pr_number), "--body", body)


def approve_and_merge(pr_number: int) -> None:
    gh("pr", "review", str(pr_number), "--approve", "--body", "All cases passed 4-layer review.")
    gh("pr", "merge", str(pr_number), "--squash", "--delete-branch")


def close_pr(pr_number: int, reason: str) -> None:
    post_comment(pr_number, f"Closing PR:\n\n{reason}")
    gh("pr", "close", str(pr_number))


def main():
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prs = list_open_case_prs()

    if not prs:
        print("No pending PRs to review")
        return

    existing_summaries = [{
        "case_id": c.get("case_id"),
        "task_category": c.get("task_category"),
        "failure_type": c.get("failure_type"),
        "tools": [t.get("name") for t in c.get("tools_attempted", [])],
        "problem_statement": c.get("problem_statement", "")[:120],
    } for c in collect_all_cases()]

    for pr in prs:
        print(f"\nReviewing PR #{pr['number']}: {pr['title']}")
        added = extract_added_cases(pr["number"])
        if not added:
            print("  No new cases detected, skipping")
            continue

        rejection = None
        for case in added:
            if not run_redact(case):
                rejection = f"❌ Redaction failed for case `{case.get('case_id')}` — sensitive content detected."
                break

            fact = run_fact_check(client, case)
            if fact.get("verdict") != "approve":
                rejection = f"❌ Fact review rejected `{case.get('case_id')}`: {fact.get('reject_code')} — {fact.get('reason','')}"
                break

            priv = run_privacy_check(client, case, existing_summaries)
            if priv.get("verdict") != "approve":
                rejection = f"❌ Privacy review rejected `{case.get('case_id')}`: {priv.get('reject_code')} — {priv.get('reason','')}"
                break

        if rejection:
            close_pr(pr["number"], rejection)
            print(f"  Closed: {rejection[:80]}")
        else:
            approve_and_merge(pr["number"])
            print(f"  Merged {len(added)} case(s)")


if __name__ == "__main__":
    main()
```

---

## File 12: scripts/reviewer/review_case_issues.py

```python
"""
AgentRX Reviewer — daily review of case-report Issues.

Contributors or external AIs may submit cases as Issues (using the template).
This script reviews each open issue labeled 'case-report' the same way as 
PRs: 4-layer review. If approved, it creates a PR that adds the case;
if rejected, it closes the issue with a comment.
"""

import os
import json
import re
import subprocess
from pathlib import Path
from anthropic import Anthropic


REPO_ROOT = Path(__file__).parent.parent.parent
COLLECTOR_DIR = REPO_ROOT / "scripts" / "collector"
FACT_PROMPT = (COLLECTOR_DIR / "prompts" / "fact_check.md").read_text(encoding="utf-8")
PRIV_PROMPT = (COLLECTOR_DIR / "prompts" / "privacy_check.md").read_text(encoding="utf-8")
REDACT_SCRIPT = REPO_ROOT / "scripts" / "redact.py"


def gh(*args, capture=True):
    return subprocess.run(["gh", *args], capture_output=capture, text=True, cwd=REPO_ROOT, check=False)


def list_pending_issues():
    r = gh("issue", "list", "--state", "open", "--label", "case-report",
           "--json", "number,title,body,labels", "--limit", "50")
    if r.returncode != 0:
        return []
    issues = json.loads(r.stdout)
    # Skip issues that already have verdict labels
    return [i for i in issues if not any(
        l["name"] in ("privacy-blocked", "ready-to-merge", "ai-rejected", "ai-merged")
        for l in i.get("labels", [])
    )]


def extract_json_from_issue(body: str) -> dict | None:
    match = re.search(r"```json\s*\n(.*?)\n```", body, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def collect_existing_summaries():
    cases = []
    by_task = REPO_ROOT / "cases" / "by-task"
    if not by_task.exists():
        return cases
    for f in by_task.glob("*.json"):
        try:
            data = json.load(open(f))
            for c in data.get("cases", []):
                cases.append({
                    "case_id": c.get("case_id"),
                    "task_category": c.get("task_category"),
                    "failure_type": c.get("failure_type"),
                    "tools": [t.get("name") for t in c.get("tools_attempted", [])],
                    "problem_statement": c.get("problem_statement", "")[:120],
                })
        except Exception:
            pass
    return cases


def run_redact(case):
    tmp = REPO_ROOT / f"_tmp_{case.get('case_id','x')}.json"
    tmp.write_text(json.dumps(case, ensure_ascii=False))
    try:
        r = subprocess.run(
            ["python3", str(REDACT_SCRIPT), "--input", str(tmp), "--strict", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0, r.stdout
    finally:
        tmp.unlink(missing_ok=True)


def claude_review(client, model, prompt, user_msg, max_tokens=1000, temp=0.1):
    msg = client.messages.create(
        model=model, max_tokens=max_tokens, temperature=temp,
        system=prompt, messages=[{"role": "user", "content": user_msg}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except Exception:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR", "reason": "non-JSON"}


def create_pr_for_issue(issue_number: int, case: dict) -> None:
    """Create a branch with the case added, then open a PR."""
    branch = f"auto-case-{case['case_id']}"
    subprocess.run(["git", "checkout", "-b", branch], cwd=REPO_ROOT, check=True)

    category = case["task_category"]
    target = REPO_ROOT / "cases" / "by-task" / f"{category}.json"
    if target.exists():
        data = json.load(open(target))
    else:
        data = {"task_category": category, "version": "0.2.0", "cases": []}

    clean = {k: v for k, v in case.items() if not k.startswith("_")}
    data["cases"].append(clean)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    subprocess.run(["git", "config", "user.name", "agentrx-bot"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "bot@agentrx.local"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "add", "cases/"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"auto: add case {case['case_id']} from issue #{issue_number}"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=REPO_ROOT, check=True)

    gh("pr", "create",
       "--title", f"Add case {case['case_id']} (issue #{issue_number})",
       "--body", f"Auto-merged after 4-layer review. Closes #{issue_number}.",
       "--label", "auto-approved")

    subprocess.run(["git", "checkout", "main"], cwd=REPO_ROOT, check=True)


def main():
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    issues = list_pending_issues()

    if not issues:
        print("No pending case-report issues")
        return

    existing = collect_existing_summaries()

    for issue in issues:
        num = issue["number"]
        print(f"\nReviewing issue #{num}: {issue['title']}")

        case = extract_json_from_issue(issue.get("body", ""))
        if not case:
            gh("issue", "comment", str(num),
               "--body", "⚠️ No valid JSON case block found. Please include a ```json code block with your case data.")
            gh("issue", "edit", str(num), "--add-label", "needs-revision")
            continue

        redact_pass, redact_out = run_redact(case)
        if not redact_pass:
            gh("issue", "comment", str(num),
               "--body", f"❌ Redaction blocked submission:\n```\n{redact_out}\n```")
            gh("issue", "edit", str(num), "--add-label", "privacy-blocked")
            gh("issue", "close", str(num))
            continue

        fact = claude_review(
            client, "claude-sonnet-4-6", FACT_PROMPT,
            f"Review:\n```json\n{json.dumps(case, indent=2)}\n```",
            max_tokens=800, temp=0.1,
        )
        if fact.get("verdict") != "approve":
            gh("issue", "comment", str(num),
               "--body", f"❌ Fact review rejected: **{fact.get('reject_code')}** — {fact.get('reason','')}")
            gh("issue", "edit", str(num), "--add-label", "ai-rejected")
            gh("issue", "close", str(num))
            continue

        priv = claude_review(
            client, "claude-opus-4-6", PRIV_PROMPT,
            f"Existing:\n```json\n{json.dumps(existing[:50], indent=1)}\n```\n\nNew:\n```json\n{json.dumps(case, indent=2)}\n```",
            max_tokens=1000, temp=0.0,
        )
        if priv.get("verdict") != "approve":
            gh("issue", "comment", str(num),
               "--body", f"❌ Privacy review rejected: **{priv.get('reject_code')}** — {priv.get('reason','')}")
            gh("issue", "edit", str(num), "--add-label", "ai-rejected")
            gh("issue", "close", str(num))
            continue

        # All passed — create PR
        try:
            create_pr_for_issue(num, case)
            gh("issue", "comment", str(num), "--body", "✅ All 4 layers approved. PR created and auto-merged.")
            gh("issue", "edit", str(num), "--add-label", "ai-merged")
        except Exception as e:
            gh("issue", "comment", str(num), "--body", f"Review passed but PR creation failed: {e}")


if __name__ == "__main__":
    main()
```

---

## File 13: scripts/monitoring/health_report.py

```python
"""
AgentRX Monitoring — weekly health report.

Generates a summary Issue with pass rates, bottleneck signals, and 
actionable warnings. Posted every Monday.
"""

import os
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter


REPO_ROOT = Path(__file__).parent.parent.parent
STATE_DIR = REPO_ROOT / "scripts" / "collector" / "state"


def analyze_week():
    today = datetime.now(timezone.utc)
    stats = {
        "raw_total": 0, "extracted_total": 0, "extract_skipped": 0,
        "fact_approved": 0, "fact_rejected": 0,
        "privacy_approved": 0, "privacy_rejected": 0,
        "reject_codes": Counter(),
    }

    for days_ago in range(7):
        date = (today - timedelta(days=days_ago)).strftime("%Y%m%d")

        raw = STATE_DIR / f"raw_{date}.jsonl"
        if raw.exists():
            stats["raw_total"] += sum(1 for _ in open(raw))

        extracted = STATE_DIR / f"extracted_{date}.json"
        if extracted.exists():
            data = json.load(open(extracted))
            stats["extracted_total"] += len(data.get("cases", []))
            stats["extract_skipped"] += len(data.get("skipped", []))

        fact = STATE_DIR / f"fact_reviewed_{date}.json"
        if fact.exists():
            data = json.load(open(fact))
            stats["fact_approved"] += len(data.get("approved", []))
            for r in data.get("rejected", []):
                stats["fact_rejected"] += 1
                stats["reject_codes"][r["verdict"].get("reject_code", "UNKNOWN")] += 1

        priv = STATE_DIR / f"privacy_reviewed_{date}.json"
        if priv.exists():
            data = json.load(open(priv))
            stats["privacy_approved"] += len(data.get("approved", []))
            for r in data.get("rejected", []):
                stats["privacy_rejected"] += 1
                stats["reject_codes"][r["verdict"].get("reject_code", "UNKNOWN")] += 1

    return stats


def pct(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "N/A"


def render_report(stats):
    raw = stats["raw_total"]
    extracted = stats["extracted_total"]
    fact_ok = stats["fact_approved"]
    priv_ok = stats["privacy_approved"]

    end_to_end = pct(priv_ok, raw)

    lines = [
        "# AgentRX Weekly Health Report",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d UTC')}_",
        "",
        "## Throughput",
        f"- Raw materials fetched: {raw}",
        f"- Extracted to cases: {extracted} ({pct(extracted, raw)})",
        f"- Passed fact review: {fact_ok} ({pct(fact_ok, extracted)})",
        f"- Passed privacy review: {priv_ok} ({pct(priv_ok, fact_ok)})",
        f"- **End-to-end pass rate: {end_to_end}**",
        "",
        "## Rejection reasons (top 5)",
    ]
    for code, count in stats["reject_codes"].most_common(5):
        lines.append(f"- `{code}`: {count}")

    lines.append("")
    lines.append("## Warnings")

    warnings = []
    if raw > 0 and priv_ok / raw < 0.1:
        warnings.append("[!] End-to-end pass rate below 10%. Review may be too strict or upstream sources weak.")
    if raw > 0 and priv_ok / raw > 0.5:
        warnings.append("[!] End-to-end pass rate above 50%. Review may be too lenient — check output quality.")
    if stats["reject_codes"].get("DUPLICATE", 0) > stats["fact_approved"] * 0.4:
        warnings.append("[!] High duplicate rate — consider expanding source diversity.")
    if stats["reject_codes"].get("PRIVACY_LEAK", 0) > 3:
        warnings.append("[!] Multiple privacy leaks caught by L3 — redact.py may need pattern additions.")

    if not warnings:
        warnings.append("_No warnings — pipeline healthy._")

    lines.extend(warnings)
    return "\n".join(lines)


def post_issue(body: str):
    title = f"Weekly Health Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body, "--label", "health-report"],
        cwd=REPO_ROOT, check=True,
    )


def main():
    stats = analyze_week()
    report = render_report(stats)
    print(report)
    post_issue(report)


if __name__ == "__main__":
    main()
```

---

## File 14: scripts/monitoring/adversarial_test.py

```python
"""
AgentRX Monitoring — weekly adversarial test.

Runs known-bad fixtures through the pipeline to verify the review layers 
still reject them correctly. Catches regressions in review prompts.
"""

import os
import json
import subprocess
from pathlib import Path
from anthropic import Anthropic


REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = Path(__file__).parent / "adversarial_fixtures"
COLLECTOR_DIR = REPO_ROOT / "scripts" / "collector"
FACT_PROMPT = (COLLECTOR_DIR / "prompts" / "fact_check.md").read_text(encoding="utf-8")
PRIV_PROMPT = (COLLECTOR_DIR / "prompts" / "privacy_check.md").read_text(encoding="utf-8")
REDACT_SCRIPT = REPO_ROOT / "scripts" / "redact.py"


def run_redact(case):
    tmp = REPO_ROOT / "_adv_tmp.json"
    tmp.write_text(json.dumps(case))
    try:
        r = subprocess.run(
            ["python3", str(REDACT_SCRIPT), "--input", str(tmp), "--strict", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    finally:
        tmp.unlink(missing_ok=True)


def claude_review(client, model, prompt, user_msg, temp=0.1):
    msg = client.messages.create(
        model=model, max_tokens=1000, temperature=temp,
        system=prompt, messages=[{"role": "user", "content": user_msg}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except Exception:
        return {"verdict": "reject", "reject_code": "PARSE_ERROR"}


def main():
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Expected outcomes per fixture
    fixtures = {
        "bad_privacy.json": {"expected": "reject", "layer": "redact_or_privacy"},
        "bad_vague.json": {"expected": "reject", "layer": "fact"},
        "bad_inconsistent.json": {"expected": "reject", "layer": "fact"},
        "bad_duplicate.json": {"expected": "reject", "layer": "privacy"},
        "good_baseline.json": {"expected": "approve", "layer": "all"},
    }

    results = []
    for name, expectation in fixtures.items():
        path = FIXTURES_DIR / name
        if not path.exists():
            print(f"[skip] missing fixture {name}")
            continue

        case = json.load(open(path))
        result = {"fixture": name, "expected": expectation["expected"]}

        redact_pass = run_redact(case)
        if not redact_pass:
            result["outcome"] = "reject"
            result["caught_by"] = "redact"
        else:
            fact = claude_review(client, "claude-sonnet-4-6", FACT_PROMPT,
                f"```json\n{json.dumps(case, indent=2)}\n```", temp=0.1)
            if fact.get("verdict") != "approve":
                result["outcome"] = "reject"
                result["caught_by"] = f"fact/{fact.get('reject_code')}"
            else:
                priv = claude_review(client, "claude-opus-4-6", PRIV_PROMPT,
                    f"Existing: []\n\n```json\n{json.dumps(case, indent=2)}\n```", temp=0.0)
                if priv.get("verdict") != "approve":
                    result["outcome"] = "reject"
                    result["caught_by"] = f"privacy/{priv.get('reject_code')}"
                else:
                    result["outcome"] = "approve"
                    result["caught_by"] = "none"

        result["pass"] = (result["outcome"] == expectation["expected"])
        results.append(result)
        status = "✓" if result["pass"] else "✗"
        print(f"{status} {name}: expected {result['expected']}, got {result['outcome']} (caught by {result['caught_by']})")

    # Post a report issue
    all_pass = all(r["pass"] for r in results)
    title = f"Adversarial Test — {'PASS' if all_pass else 'FAIL'}"
    body_lines = [f"# Adversarial Test Results\n"]
    for r in results:
        icon = "✅" if r["pass"] else "❌"
        body_lines.append(
            f"{icon} **{r['fixture']}**: expected `{r['expected']}`, got `{r['outcome']}` (caught by `{r['caught_by']}`)"
        )
    body = "\n".join(body_lines)
    labels = "adversarial-test" + ("" if all_pass else ",regression")

    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body, "--label", labels],
        cwd=REPO_ROOT, check=True,
    )


if __name__ == "__main__":
    main()
```

---

## File 15: scripts/monitoring/adversarial_fixtures/bad_privacy.json

```json
{
  "case_id": "2026-04-16-adv001",
  "timestamp": "2026-04-16T00:00:00Z",
  "platform": "claude-code",
  "task_category": "data-analysis",
  "tools_attempted": [{"name": "xlsx", "type": "skill", "outcome": "error"}],
  "failure_type": "execution_error",
  "problem_statement": "When processing ACME Corp Q3 2024 revenue data for client John Smith at john@acme.com, the xlsx skill failed on the file /Users/sarah/projects/acme-q3/revenue.xlsx",
  "environment": {"model": "claude-sonnet-4-6", "os": "macos"},
  "remedy": "Check file permissions on /Users/sarah/projects/acme-q3/revenue.xlsx and retry",
  "remedy_type": "change_tool_params",
  "confidence": "high",
  "source_category": "reddit",
  "verified": false
}
```

---

## File 16: scripts/monitoring/adversarial_fixtures/bad_vague.json

```json
{
  "case_id": "2026-04-16-adv002",
  "timestamp": "2026-04-16T00:00:00Z",
  "platform": "claude-code",
  "task_category": "other",
  "tools_attempted": [{"name": "some-skill", "type": "skill", "outcome": "error"}],
  "failure_type": "unknown",
  "problem_statement": "The tool didn't work well and the output was bad. Users reported issues.",
  "environment": {"model": "unknown", "os": "unknown"},
  "remedy": "Improve the tool. Fix the bugs. Make it better.",
  "remedy_type": "other",
  "confidence": "low",
  "source_category": "reddit",
  "verified": false
}
```

---

## File 17: scripts/monitoring/adversarial_fixtures/bad_inconsistent.json

```json
{
  "case_id": "2026-04-16-adv003",
  "timestamp": "2026-04-16T00:00:00Z",
  "platform": "claude-code",
  "task_category": "web-browsing",
  "tools_attempted": [{"name": "browser-cdp", "type": "skill", "outcome": "worked-but-suboptimal"}],
  "failure_type": "execution_error",
  "problem_statement": "The browser-cdp skill returned high quality HTML but the quality wasn't good enough for visualization purposes.",
  "environment": {"model": "claude-sonnet-4-6", "os": "linux"},
  "recommended_tool": {"name": "pdf", "type": "skill", "why": "handles PDFs better"},
  "remedy": "Reformat the spreadsheet with a new template",
  "remedy_type": "switch_tool",
  "confidence": "high",
  "source_category": "github-issue",
  "verified": false
}
```

---

## File 18: scripts/monitoring/adversarial_fixtures/bad_duplicate.json

This fixture should be identical in pattern to an existing case in `cases/by-task/visualization.json` (e.g., the pptx multi-skill conflict case). Write a case with the same task_category, failure_type, and tools but a different case_id.

```json
{
  "case_id": "2026-04-16-adv004",
  "timestamp": "2026-04-16T00:00:00Z",
  "platform": "claude-ai",
  "task_category": "visualization",
  "tools_attempted": [{"name": "pptx", "type": "skill", "outcome": "worked-but-suboptimal"}],
  "failure_type": "wrong_tool_selected",
  "problem_statement": "User requested a slide deck and multiple pptx-producing skills were loaded. The general pptx skill activated instead of a more specialized one.",
  "environment": {"model": "claude-sonnet-4-6", "other_active_tools": ["pptx", "brand-deck"]},
  "recommended_tool": {"name": "brand-deck", "type": "skill", "why": "more specialized"},
  "remedy": "Prefer specialized slide-generation skills over the generic pptx skill when both are installed.",
  "remedy_type": "switch_tool",
  "confidence": "high",
  "source_category": "reddit",
  "verified": false
}
```

---

## File 19: scripts/monitoring/adversarial_fixtures/good_baseline.json

```json
{
  "case_id": "2026-04-16-adv005",
  "timestamp": "2026-04-16T00:00:00Z",
  "platform": "claude-code",
  "task_category": "communication",
  "tools_attempted": [{"name": "slack-webhook", "type": "skill", "outcome": "not-triggered"}],
  "failure_type": "tool_not_triggered",
  "problem_statement": "A webhook skill for posting to Slack was installed but failed to trigger when the user asked to 'notify the team'. The skill's description only matched on 'send slack message' phrasing, missing semantic variants.",
  "environment": {"model": "claude-sonnet-4-6", "os": "macos"},
  "recommended_tool": {"name": "slack-webhook", "type": "skill", "why": "correct tool, needs better description"},
  "remedy": "Expand the slack-webhook skill description to include natural-language triggers like 'notify team', 'ping channel', 'alert team' — not just the literal 'send slack message' pattern.",
  "remedy_type": "update_description",
  "confidence": "high",
  "source_category": "blog",
  "verified": false
}
```

---

## File 20: .github/workflows/daily_case_collection.yml

```yaml
name: Daily Case Collection

on:
  schedule:
    - cron: '0 2 * * *'   # 02:00 UTC daily
  workflow_dispatch:

jobs:
  collect:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: L1 — Discover raw materials
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}
        run: python scripts/collector/discover.py

      - name: L1 — Extract structured cases
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/collector/extract.py

      - name: L2 — Fact review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/collector/fact_check.py

      - name: L3 — Privacy & value review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/collector/privacy_check.py

      - name: Auto-merge approved cases
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/collector/auto_merge.py

      - name: Persist state
        run: |
          git config user.name "agentrx-bot"
          git config user.email "bot@agentrx.local"
          git add scripts/collector/state/
          git commit -m "chore: update collection state" --allow-empty
          git push
```

---

## File 21: .github/workflows/daily_pr_review.yml

```yaml
name: Daily PR and Issue Review

on:
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC daily (4 hours after collection)
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Review pending PRs
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/reviewer/review_pending_prs.py

      - name: Review pending case-report issues
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/reviewer/review_case_issues.py
```

---

## File 22: .github/workflows/weekly_health_report.yml

```yaml
name: Weekly Health Report

on:
  schedule:
    - cron: '0 10 * * 1'   # 10:00 UTC every Monday
  workflow_dispatch:

jobs:
  report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate health report
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/monitoring/health_report.py
```

---

## File 23: .github/workflows/adversarial_test.yml

```yaml
name: Weekly Adversarial Test

on:
  schedule:
    - cron: '0 12 * * 1'   # 12:00 UTC every Monday (after health report)
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run adversarial test
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/monitoring/adversarial_test.py
```

---

## Post-setup checklist for Claude Code

After you have created all files, perform these operations in order:

1. **Make scripts executable** (for any shell hooks):
   ```bash
   chmod +x scripts/collector/*.py scripts/reviewer/*.py scripts/monitoring/*.py
   ```

2. **Verify directory structure exists**:
   ```bash
   tree -L 4 scripts/ .github/
   ```

3. **Verify secrets are set in GitHub**:
   Tell the user to add these secrets at 
   `Settings > Secrets and variables > Actions`:
   - `ANTHROPIC_API_KEY`
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`

4. **Create initial state files**:
   ```bash
   mkdir -p scripts/collector/state
   echo '{}' > scripts/collector/state/processed_hashes.json
   touch scripts/collector/state/.gitkeep
   ```

5. **Initial commit**:
   ```bash
   git add .
   git commit -m "feat: add automated case collection and review pipeline

   - 4-layer AI review pipeline (redact + extract + fact + privacy)
   - Daily case collection from 6 sources
   - Daily PR/issue review for external contributions
   - Weekly health monitoring and adversarial testing
   - Fully automated, no human review required"
   git push
   ```

6. **Test manually before waiting for cron**:
   Tell the user to trigger workflows manually via the Actions tab
   using "Run workflow" to verify each runs correctly.

7. **Optional: create calibration branch**:
   For the first 2 weeks, suggest running in a branch where cases are 
   merged to `cases/pending/` instead of `cases/by-task/`, so the user 
   can spot-check quality. Switch to full auto when confidence is high.

## Expected behavior after first run

- `scripts/collector/state/` will contain `raw_YYYYMMDD.jsonl`, 
  `extracted_YYYYMMDD.json`, `fact_reviewed_YYYYMMDD.json`, 
  `privacy_reviewed_YYYYMMDD.json`, and updated `processed_hashes.json`
- `cases/by-task/*.json` files will have new cases appended
- `cases/index.json` will be regenerated
- A commit from `agentrx-bot` will be pushed to main

If a day produces zero approved cases, the workflow still runs without 
error — that is normal and expected.

## Cost expectations

- ~$0.70/day for the collection pipeline
- ~$0.30/day for PR/issue review (varies with volume)
- ~$0.50/week for monitoring tasks
- **Total monthly cost: ~$30-40** with typical volume
