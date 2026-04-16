# Repository audit — what needed updating

This audit reflects the current repository structure and why each file needed change.

## Files that clearly required update

### README.md
Reason:
- still describes the project as skill-first
- still presents cases as `by-skill/` and `by-type/`
- still frames the main question as “which skill failed?”

### SKILL.md
Reason:
- activation and diagnosis centered on skill failures
- retrieval assumes `skill_triggered + failure_type`
- does not force local self-diagnosis before search

### schema/case.schema.json
Reason:
- old schema centers on `skill_triggered`
- missing task / stage / alternative-route structure
- remedy field too generic for action routing

### rules/failure_types.yaml
Reason:
- old taxonomy is still failure-first and skill-leaning
- does not cleanly separate environment/config/invocation/capability fit
- missing task-framing and better-alternative families

### CONTRIBUTING.md
Reason:
- contribution guidance still asks mainly for skill failure reports
- needs task-journey guidance

### hooks/README.md
Reason:
- legacy framing still too tied to skill errors
- needs clearer hook-vs-diagnosis boundary

### .github/ISSUE_TEMPLATE/case_report.yml
Reason:
- old form asks for skill-triggered failure
- needs task/stage/symptom/next-action fields

### .github/workflows/validate_case.yml
Reason:
- wording should align with the v2 contribution model
- script assumptions may need follow-up after schema migration

### cases/index.json
Reason:
- legacy routing index is not task-first

## Files that may need later implementation work

### scripts/redact.py
Needs review to ensure:
- new fields are allowed
- privacy rules reflect task-first cases
- legacy assumptions do not reject useful v2 structure

### scripts/submit_case.sh
Needs review to ensure:
- generated payload matches v2 schema
- issue template population is updated

### tests/test_redact.py
Needs new cases for:
- task goal phrasing
- alternative tool lists
- recommendation detail
- new privacy edge cases

## Migration posture

This update intentionally changes the information architecture first.
Implementation files can be brought fully in sync next.
