# Case Collection Plan — v2

## Goal

Collect the first **200 task-first cases** without relying mainly on manual self-testing.

The target is not “200 tool complaints.”  
The target is **200 usable navigation cases** that reflect real AI journeys.

## What changed from the old collection plan

Old logic:
- collect skill complaints
- group by skill
- classify by failure type

New logic:
- collect real task journeys
- identify which tools were used in the journey
- capture where the journey broke
- record what next action or alternative solved it

The unit of value is now:

> **task + stage + symptom + current tool path + next action**

## Target coverage model

### High-frequency tasks first
Define 10–12 high-frequency task categories.

Suggested initial targets:

1. browse-web
2. read-files
3. transform-documents
4. create-presentation
5. analyze-data
6. code-editing
7. workflow-automation
8. communicate-and-publish
9. create-visual-assets
10. search-and-compare-tools
11. local-environment-setup
12. monitor-and-check

### Coverage target
Aim for:
- 12 categories
- 12–20 raw usable cases each
- 200 final accepted cases

## Source strategy

### Tier A — GitHub issues and discussions
Best for:
- reproducible setup pain
- installation/configuration problems
- alternative tool debates
- recovery threads

Look for:
- skill repos
- MCP repos
- plugin repos
- agent repos
- “which tool should I use” discussions

### Tier B — Reddit / HN / forum threads
Best for:
- real frustration language
- symptom descriptions
- task-vs-tool mismatch
- “I switched from X to Y and it worked” stories

### Tier C — blog posts / postmortems / tool comparisons
Best for:
- cleaner narratives
- stronger recommendation detail
- tradeoff explanation

### Tier D — comments on tool directories / marketplaces / repo README threads
Best for:
- lightweight but repeated pain points
- recurring capability mismatch patterns

## Collection lens

Do not ask only:
- “What failed?”

Also ask:
- What task was the user trying to finish?
- What tool family did they pick first?
- Why did that path underperform?
- What did they switch to?
- Was the real issue config, environment, invocation, capability fit, or task framing?

## Intake spreadsheet columns

Use a sheet or CSV with at least:

- source_url
- source_type
- date_found
- platform
- task_category_guess
- task_goal_abstract
- journey_stage_guess
- observed_symptom
- tool_triggered
- tool_type
- alternative_tool_mentions
- suspected_problem_family_guess
- raw_quote
- outcome_guess
- signal_quality
- notes

## Qualification filter

A source can become a case only if all are true:

- the task is identifiable
- the symptom is identifiable
- the current tool path is identifiable or strongly inferable
- the next action or stronger alternative is identifiable or strongly inferable
- the source is not only “model is dumb”

Reject:
- vague complaints
- pure prompt complaints with no tool-path relevance
- cases that expose private context
- one-off noise with no reusable pattern

## AI-assisted transformation pipeline

### Step 1
Collect 400–600 raw snippets.

### Step 2
Filter down to 260–300 promising snippets.

### Step 3
Transform them with AI into the v2 case schema.

### Step 4
Run privacy / schema validation.

### Step 5
Deduplicate into 200 strong accepted cases.

## Transformation prompt skeleton

```text
You are converting a real-world AI tool-path complaint or recovery story into a v2 case.

Output only valid JSON.

Rules:
1. Preserve the task and recovery logic.
2. Remove private details.
3. Focus on:
   - task_category
   - task_goal
   - journey_stage
   - observed_symptom
   - tool_triggered / tool_type
   - suspected_problem_family
   - attempted_actions
   - recommended_next_step
   - alternatives_considered
4. Do not invent facts. Use "unknown" when necessary.
5. If the snippet is too weak to create a reusable case, return {"skip": true}.
```

## Deduplication logic

Group primarily by:
- task_category
- journey_stage
- suspected_problem_family
- tool_triggered
- recommended_next_step

Keep multiple cases only when they teach meaningfully different:
- constraints
- tradeoffs
- recovery routes

## Weekly operating rhythm

### Batch 1
- choose 2 task categories
- collect 60 raw snippets
- transform 25–30 cases
- review quality

### Batch 2
- expand to 4 more categories
- refine taxonomy where needed
- update case prompt if low-quality output appears

### Batch 3+
- fill remaining categories
- bias toward repeated pain patterns
- avoid overfitting to one hot tool repo

## First 30 cases should over-index on these patterns

- browse-web + capability_mismatch
- browse-web + better_alternative_exists
- local-environment-setup + configuration
- create-presentation + task_framing_issue
- analyze-data + quality_miss
- workflow-automation + hook_vs_model_boundary
- code-editing + recovery_gap
- read-files + invocation

## Success metric

The collection effort succeeds if another agent can use the cases to answer:

- what kind of situation am I in
- what should I try next
- which tool family is stronger here
- when should I stop retrying the same path
