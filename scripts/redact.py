#!/usr/bin/env python3
"""
Skill Doctor — Deterministic Redaction Script

Runs BEFORE any case is submitted to GitHub.
This is the hard privacy layer — it catches what the LLM's prompt-level
instructions might miss.

Usage:
    python3 redact.py --input case.json [--output redacted.json] [--strict]
    
Exit codes:
    0 — Clean, safe to submit
    1 — Redaction applied, review recommended
    2 — Blocked: too much sensitive content detected, do not submit
    3 — Invalid input
"""

import json
import re
import sys
import argparse
import hashlib
from datetime import datetime
from pathlib import Path


# ── Patterns that should NEVER appear in a case report ──

PATTERNS = {
    "email": re.compile(r'[a-zA-Z0-9._%+\u00c0-\u024f]+@[a-zA-Z0-9\u00c0-\u024f.-]+\.[a-zA-Z]{2,}'),
    "url": re.compile(r'https?://[^\s"\'<>]+'),
    "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "file_path_unix": re.compile(r'(?:/[a-zA-Z0-9._-]+){3,}'),
    "file_path_windows": re.compile(r'[A-Z]:\\(?:[^\s\\]+\\)*[^\s\\]+'),
    "api_key_generic": re.compile(r'(?:sk|pk|api|key|token|secret|bearer)[_-]?[a-zA-Z0-9]{16,}', re.IGNORECASE),
    "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
    "phone": re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'),
    "uuid": re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
    "base64_long": re.compile(r'[A-Za-z0-9+/=]{40,}'),
}

# Allowed URL patterns (these are OK to keep)
ALLOWED_URLS = [
    re.compile(r'https?://raw\.githubusercontent\.com/'),
    re.compile(r'https?://github\.com/'),
    re.compile(r'https?://clawhub\.ai/'),
]

# Fields where we check for sensitive content
TEXT_FIELDS = [
    "failure_signature",
    "user_correction",
    "remedy",
]

# Environment sub-fields to check
ENV_TEXT_FIELDS = [
    "context_note",
]

# ── Business content heuristics ──

BUSINESS_KEYWORDS = re.compile(
    r'\b('
    r'Q[1-4]\s*\d{2,4}|'            # Q1 2024, Q3 25
    r'(?:fiscal|financial)\s+year|'
    r'revenue|profit|loss|earnings|'
    r'(?:sales|marketing)\s+(?:report|data|pipeline)|'
    r'client\s+(?:name|list|data)|'
    r'customer\s+(?:name|list|data|record)|'
    r'employee\s+(?:name|list|record)|'
    r'invoice|purchase\s+order|contract|'
    r'(?:board|investor)\s+(?:meeting|presentation|deck)|'
    r'(?:confidential|proprietary|internal\s+only)'
    r')\b',
    re.IGNORECASE
)

# File extension patterns that suggest real file references
FILE_EXTENSIONS = re.compile(
    r'\b\w+\.(?:xlsx?|docx?|pptx?|pdf|csv|json|ya?ml|py|js|ts|sql|md|txt|html|css)\b',
    re.IGNORECASE
)


class RedactionResult:
    def __init__(self):
        self.issues = []        # (field, pattern_name, matched_text)
        self.redactions = []    # (field, original, redacted)
        self.blocked = False
        self.block_reason = ""

    @property
    def clean(self):
        return len(self.issues) == 0 and len(self.redactions) == 0

    def add_issue(self, field, pattern_name, matched):
        self.issues.append((field, pattern_name, matched))

    def add_redaction(self, field, original, redacted):
        self.redactions.append((field, original, redacted))

    def block(self, reason):
        self.blocked = True
        self.block_reason = reason

    def summary(self):
        lines = []
        if self.blocked:
            lines.append(f"[BLOCKED] {self.block_reason}")
        for field, pattern, matched in self.issues:
            preview = matched[:40] + "..." if len(matched) > 40 else matched
            lines.append(f"  [{field}] detected {pattern}: {preview}")
        for field, orig, new in self.redactions:
            lines.append(f"  [{field}] redacted: {orig[:30]}... → {new[:30]}...")
        if not lines:
            lines.append("  [OK] No sensitive content detected")
        return "\n".join(lines)


def is_allowed_url(url: str) -> bool:
    return any(p.match(url) for p in ALLOWED_URLS)


def redact_string(value: str, field_name: str, result: RedactionResult) -> str:
    """Scan a string value and redact sensitive patterns."""
    redacted = value

    for pattern_name, pattern in PATTERNS.items():
        matches = pattern.findall(redacted)
        for match in matches:
            # Special case: allow certain URLs (check before URL pattern processing)
            if pattern_name == "url":
                if is_allowed_url(match):
                    continue
            # Special case: allow GitHub URLs even if they look like file paths
            if "githubusercontent.com" in match or "github.com" in match:
                continue
            # Special case: don't flag skill names that look like file paths
            if pattern_name == "file_path_unix" and match.startswith("/mnt/skills/"):
                continue

            result.add_issue(field_name, pattern_name, match)
            placeholder = f"[REDACTED_{pattern_name.upper()}]"
            redacted = redacted.replace(match, placeholder)
            result.add_redaction(field_name, match, placeholder)

    # Check for business content
    biz_matches = BUSINESS_KEYWORDS.findall(redacted)
    for match in biz_matches:
        result.add_issue(field_name, "business_content", match)

    # Check for file extension references (e.g. "report.xlsx")
    file_matches = FILE_EXTENSIONS.findall(redacted)
    for match in file_matches:
        # Skill names ending in common extensions are OK
        allowed_filenames = {"SKILL.md", "index.json", "case.schema.json", "redact.py", "submit_case.sh", "schema.json"}
        if match in allowed_filenames:
            continue
        result.add_issue(field_name, "file_reference", match)

    return redacted


def validate_schema(case: dict) -> list:
    """Basic structural validation (no jsonschema dependency needed)."""
    errors = []
    required = [
        "case_id", "timestamp", "platform", "skill_triggered",
        "failure_type", "failure_signature", "environment", "remedy"
    ]
    for field in required:
        if field not in case:
            errors.append(f"Missing required field: {field}")

    valid_platforms = ["claude-code", "claude-ai", "openclaw", "codex", "cursor", "gemini-cli", "other"]
    if case.get("platform") and case["platform"] not in valid_platforms:
        errors.append(f"Invalid platform: {case['platform']}")

    valid_types = [
        "wrong_skill_selected", "skill_conflict", "skill_not_triggered",
        "tool_error", "environment_issue", "context_overflow",
        "description_mismatch", "should_use_hook", "output_quality", "unknown"
    ]
    if case.get("failure_type") and case["failure_type"] not in valid_types:
        errors.append(f"Invalid failure_type: {case['failure_type']}")

    # Length checks
    if len(case.get("failure_signature", "")) > 300:
        errors.append("failure_signature exceeds 300 characters")
    if len(case.get("remedy", "")) > 500:
        errors.append("remedy exceeds 500 characters")
    if len(case.get("user_correction", "")) > 200:
        errors.append("user_correction exceeds 200 characters")

    return errors


def redact_case(case: dict, strict: bool = False) -> tuple:
    """
    Main redaction function.
    
    Returns: (redacted_case, RedactionResult)
    """
    result = RedactionResult()

    # 1. Validate structure
    schema_errors = validate_schema(case)
    if schema_errors:
        result.block(f"Schema validation failed: {'; '.join(schema_errors)}")
        return case, result

    # 2. Redact text fields
    redacted_case = dict(case)

    for field in TEXT_FIELDS:
        if field in redacted_case and isinstance(redacted_case[field], str):
            redacted_case[field] = redact_string(
                redacted_case[field], field, result
            )

    # 3. Redact environment sub-fields
    if "environment" in redacted_case and isinstance(redacted_case["environment"], dict):
        env = dict(redacted_case["environment"])
        for field in ENV_TEXT_FIELDS:
            if field in env and isinstance(env[field], str):
                env[field] = redact_string(env[field], f"environment.{field}", result)
        redacted_case["environment"] = env

    # 4. Check for unexpected fields (data leakage via extra keys)
    allowed_keys = {
        "case_id", "timestamp", "platform", "skill_triggered", "skill_version",
        "other_active_skills", "failure_type", "failure_signature", "environment",
        "user_correction", "remedy", "remedy_type", "confidence", "verified",
        "related_cases"
    }
    extra_keys = set(redacted_case.keys()) - allowed_keys
    if extra_keys:
        for key in extra_keys:
            result.add_issue("_root", "unexpected_field", key)
            del redacted_case[key]
        result.add_redaction("_root", f"removed fields: {extra_keys}", "[REMOVED]")

    # 5. Strict mode: block if ANY issues found
    if strict and len(result.issues) > 0:
        result.block(f"Strict mode: {len(result.issues)} issue(s) detected")

    # 6. Block if too many issues (likely contains substantial sensitive content)
    if len(result.issues) > 5:
        result.block(f"Too many sensitive patterns detected ({len(result.issues)}). Case likely contains business content.")

    return redacted_case, result


def main():
    parser = argparse.ArgumentParser(
        description="Skill Doctor — Deterministic case redaction"
    )
    parser.add_argument("--input", required=True, help="Path to case JSON file")
    parser.add_argument("--output", help="Path for redacted output (default: overwrite input)")
    parser.add_argument("--strict", action="store_true", help="Block on ANY detected issue")
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't write")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(3)

    try:
        with open(input_path) as f:
            case = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(3)

    redacted, result = redact_case(case, strict=args.strict)

    print("=== Skill Doctor Redaction Report ===")
    print(result.summary())

    if result.blocked:
        print(f"\n❌ BLOCKED: {result.block_reason}")
        print("This case should NOT be submitted. Please review and rewrite.")
        sys.exit(2)

    if not result.clean:
        print(f"\n⚠️  {len(result.redactions)} redaction(s) applied.")
        print("Review the output before submitting.")

        if not args.dry_run:
            output_path = args.output or args.input
            with open(output_path, "w") as f:
                json.dump(redacted, f, indent=2, ensure_ascii=False)
            print(f"Redacted case written to: {output_path}")
        sys.exit(1)

    print("\n✅ Clean — no sensitive content detected.")
    if not args.dry_run:
        output_path = args.output or args.input
        with open(output_path, "w") as f:
            json.dump(redacted, f, indent=2, ensure_ascii=False)
        print(f"Case written to: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
