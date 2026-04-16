# Update summary

This package rewrites the project around a new core model:

`task -> journey stage -> problem family -> next action -> candidate tools/cases`

Included:
- full README rewrite
- full SKILL rewrite
- new v2 schema
- new taxonomy files
- updated contribution and issue submission docs
- new architecture / intake / migration / case collection docs
- new example case and empty v2 index

Not included:
- full implementation rewrite of `redact.py`, `submit_case.sh`, and tests
- migration of legacy case JSON files

Recommended next engineering step:
1. replace docs/config files
2. migrate 10 legacy cases by hand as calibration
3. update redaction / validation scripts
4. batch-ingest first 50 new v2 cases
