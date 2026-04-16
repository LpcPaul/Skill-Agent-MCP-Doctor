#!/usr/bin/env python3
"""Split bulk-new cases into individual by-skill files and rebuild index."""
import json
from pathlib import Path

cases_dir = Path(__file__).parent.parent / "cases"
bulk_file = cases_dir / "by-skill" / "bulk-new.json"
by_skill_dir = cases_dir / "by-skill"
by_type_dir = cases_dir / "by-type"

with open(bulk_file) as f:
    cases = json.load(f)

# Group by skill
skill_groups = {}
for case in cases:
    skill = case["skill_triggered"]
    skill_groups.setdefault(skill, []).append(case)

# Write per-skill files
for skill, skill_cases in skill_groups.items():
    safe_name = skill.replace(" ", "-").replace("/", "_")
    out_file = by_skill_dir / f"{safe_name}.json"
    with open(out_file, "w") as f:
        json.dump(skill_cases, f, indent=2, ensure_ascii=False)
    print(f"  Created {out_file.name} ({len(skill_cases)} cases)")

# Group by type
type_groups = {}
for case in cases:
    ft = case["failure_type"]
    type_groups.setdefault(ft, []).append(case)

for ftype, type_cases in type_groups.items():
    out_file = by_type_dir / f"{ftype}.json"
    existing = []
    if out_file.exists():
        with open(out_file) as f:
            existing = json.load(f)
    # Merge: skip duplicates by case_id
    existing_ids = {c["case_id"] for c in existing}
    for c in type_cases:
        if c["case_id"] not in existing_ids:
            # Only keep lightweight fields for by-type index
            existing.append({
                "case_id": c["case_id"],
                "skill_triggered": c["skill_triggered"],
                "failure_signature": c["failure_signature"],
                "remedy": c["remedy"],
                "remedy_type": c.get("remedy_type", "other"),
                "verified": c.get("verified", False)
            })
    with open(out_file, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"  Updated by-type/{ftype}.json ({len(existing)} cases)")

# Rebuild index.json
all_cases = []
# Full cases from by-skill
for skill_file in by_skill_dir.glob("*.json"):
    if skill_file.name == "bulk-new.json":
        continue
    with open(skill_file) as f:
        skill_cases = json.load(f)
        all_cases.extend(skill_cases)

# Deduplicate by case_id
seen = {}
for c in all_cases:
    if c["case_id"] not in seen:
        seen[c["case_id"]] = c

index = {
    "version": "0.2.0",
    "updated": "2026-04-15T00:00:00Z",
    "case_count": len(seen),
    "cases": list(seen.values())
}

with open(cases_dir / "index.json", "w") as f:
    json.dump(index, f, indent=2, ensure_ascii=False)

print(f"\nRebuilt index.json with {len(seen)} cases")

# Remove bulk file
bulk_file.unlink()
print("Removed bulk-new.json")
