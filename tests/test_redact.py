"""
Skill Doctor — Deterministic Redaction Script Unit Tests

Run: pytest tests/test_redact.py -v
"""

import json
import sys
import subprocess
import pytest
from pathlib import Path

# Add parent directory to path so we can import redact
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from redact import redact_case, RedactionResult, PATTERNS, BUSINESS_KEYWORDS


# ── Helpers ──

def make_case(**overrides):
    """Create a minimal valid case dict."""
    case = {
        "case_id": "2026-04-15-abc123",
        "timestamp": "2026-04-15T00:00:00Z",
        "platform": "claude-code",
        "skill_triggered": "xlsx",
        "failure_type": "wrong_skill_selected",
        "failure_signature": "Test signature",
        "environment": {"model": "claude-sonnet-4-6", "os": "macos"},
        "remedy": "Test remedy",
    }
    case.update(overrides)
    return case


# ── Schema Validation ──

class TestSchemaValidation:
    def test_valid_case_passes(self):
        case = make_case()
        redacted, result = redact_case(case)
        assert not result.blocked

    def test_missing_required_field_blocked(self):
        case = make_case()
        del case["failure_signature"]
        _, result = redact_case(case)
        assert result.blocked
        assert "Missing required field" in result.block_reason

    def test_invalid_platform_blocked(self):
        case = make_case(platform="invalid-platform")
        _, result = redact_case(case)
        assert result.blocked

    def test_invalid_failure_type_blocked(self):
        case = make_case(failure_type="not_a_real_type")
        _, result = redact_case(case)
        assert result.blocked

    def test_signature_too_long_blocked(self):
        case = make_case(failure_signature="x" * 301)
        _, result = redact_case(case)
        assert result.blocked

    def test_remedy_too_long_blocked(self):
        case = make_case(remedy="x" * 501)
        _, result = redact_case(case)
        assert result.blocked

    def test_user_correction_too_long_blocked(self):
        case = make_case(user_correction="x" * 201)
        _, result = redact_case(case)
        assert result.blocked

    def test_extra_fields_removed(self):
        case = make_case(secret_data="should be removed", internal_id="12345")
        redacted, result = redact_case(case)
        assert "secret_data" not in redacted
        assert "internal_id" not in redacted


# ── PII Detection ──

class TestPIIDetection:
    def test_email_redacted(self):
        case = make_case(failure_signature="user email is test@example.com in the system")
        redacted, result = redact_case(case)
        assert "test@example.com" not in redacted["failure_signature"]
        assert "[REDACTED_EMAIL]" in redacted["failure_signature"]

    def test_url_redacted(self):
        case = make_case(failure_signature="Error fetching https://api.example.com/v1/data")
        redacted, result = redact_case(case)
        assert "api.example.com" not in redacted["failure_signature"]

    def test_github_url_allowed(self):
        case = make_case(failure_signature="Clone from https://github.com/LpcPaul/skill-doctor")
        redacted, result = redact_case(case)
        # GitHub URLs should be allowed
        assert "github.com" in redacted["failure_signature"]

    def test_ip_address_redacted(self):
        case = make_case(failure_signature="Connection refused at 192.168.1.100:8080")
        redacted, result = redact_case(case)
        assert "192.168.1.100" not in redacted["failure_signature"]

    def test_api_key_redacted(self):
        case = make_case(failure_signature="API key sk-1234567890abcdef1234567890ab was exposed")
        redacted, result = redact_case(case)
        assert "sk-1234567890" not in redacted["failure_signature"]
        assert "[REDACTED_API_KEY_GENERIC]" in redacted["failure_signature"]

    def test_aws_key_redacted(self):
        case = make_case(failure_signature="AWS key AKIAIOSFODNN7EXAMPLE1 found in config")
        redacted, result = redact_case(case)
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted["failure_signature"]

    def test_phone_redacted(self):
        case = make_case(failure_signature="User called support at 555-123-4567")
        redacted, result = redact_case(case)
        assert "555-123-4567" not in redacted["failure_signature"]

    def test_uuid_redacted(self):
        case = make_case(failure_signature="Session ID a1b2c3d4-e5f6-7890-abcd-ef1234567890 expired")
        redacted, result = redact_case(case)
        # Full UUID should not remain intact
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" not in redacted["failure_signature"]
        # Should have at least partial redaction
        assert "[REDACTED_" in redacted["failure_signature"]

    def test_long_base64_redacted(self):
        long_b64 = "SGVsbG8gV29ybGQh" * 5  # 70 chars
        case = make_case(failure_signature=f"Token: {long_b64}")
        redacted, result = redact_case(case)
        assert long_b64 not in redacted["failure_signature"]

    def test_unix_path_redacted(self):
        case = make_case(failure_signature="Error reading /Users/john/projects/secret-api/config.yaml")
        redacted, result = redact_case(case)
        assert "/Users/john/projects" not in redacted["failure_signature"]

    def test_windows_path_redacted(self):
        case = make_case(failure_signature="File at C:\\Users\\admin\\Documents\\passwords.xlsx not found")
        redacted, result = redact_case(case)
        assert "C:\\Users" not in redacted["failure_signature"]

    def test_skills_path_allowed(self):
        case = make_case(failure_signature="Skill located at /mnt/skills/skill-doctor/SKILL.md")
        redacted, result = redact_case(case)
        # Skills paths should be allowed
        assert "/mnt/skills/skill-doctor" in redacted["failure_signature"]


# ── Business Content Detection ──

class TestBusinessContentDetection:
    def test_quarterly_report_detected(self):
        case = make_case(failure_signature="Generating Q3 2024 revenue report")
        _, result = redact_case(case)
        assert len([i for i in result.issues if i[1] == "business_content"]) > 0

    def test_client_name_detected(self):
        case = make_case(failure_signature="client name was exposed in the report")
        _, result = redact_case(case)
        assert len([i for i in result.issues if i[1] == "business_content"]) > 0

    def test_confidential_detected(self):
        case = make_case(failure_signature="This is confidential internal data")
        _, result = redact_case(case)
        assert len([i for i in result.issues if i[1] == "business_content"]) > 0

    def test_sales_pipeline_detected(self):
        case = make_case(failure_signature="sales pipeline data was included")
        _, result = redact_case(case)
        assert len([i for i in result.issues if i[1] == "business_content"]) > 0

    def test_chinese_business_keywords(self):
        """Test that Chinese business terms are caught by the regex."""
        # Note: The current BUSINESS_KEYWORDS regex is English-focused.
        # This test documents the gap — Chinese terms like "三季度" or "客户数据"
        # would NOT be caught without explicit support.
        case = make_case(failure_signature="Generating summary of project data")
        _, result = redact_case(case)
        # "project data" itself isn't flagged, but adding Chinese patterns
        # would be a future enhancement
        pass  # Documenting known gap


# ── File Reference Detection ──

class TestFileReferenceDetection:
    def test_file_extension_flagged(self):
        case = make_case(failure_signature="Opened report.xlsx and found errors")
        _, result = redact_case(case)
        assert len([i for i in result.issues if i[1] == "file_reference"]) > 0

    def test_skill_file_names_allowed(self):
        for filename in ["SKILL.md", "index.json", "case.schema.json", "redact.py", "submit_case.sh"]:
            case = make_case(failure_signature=f"File {filename} was referenced")
            _, result = redact_case(case)
            # These should NOT be flagged
            file_issues = [i for i in result.issues if i[1] == "file_reference"]
            assert len(file_issues) == 0, f"{filename} should be allowed"


# ── Unicode and Edge Cases ──

class TestUnicodeEdgeCases:
    def test_unicode_email(self):
        """Email with unicode characters."""
        case = make_case(failure_signature="Contact: üser@tëst.com was in the config")
        redacted, result = redact_case(case)
        assert "üser@tëst.com" not in redacted["failure_signature"]

    def test_chinese_text_passes(self):
        """Pure Chinese text without business keywords should pass."""
        case = make_case(
            failure_signature="用户请求生成报告但触发了错误的技能",
            user_correction="用户手动指定了正确的输出格式"
        )
        redacted, result = redact_case(case)
        # Chinese text itself is fine if no business keywords
        assert "用户" in redacted["failure_signature"]

    def test_emoji_in_signature(self):
        case = make_case(failure_signature="Spreadsheet with emoji 📊❌ failed to render")
        redacted, result = redact_case(case)
        # Emoji should not cause redaction
        assert "📊" in redacted["failure_signature"]

    def test_mixed_unicode_and_pii(self):
        case = make_case(failure_signature="用户 test@example.com 的数据被泄露")
        redacted, result = redact_case(case)
        assert "test@example.com" not in redacted["failure_signature"]
        assert "[REDACTED_EMAIL]" in redacted["failure_signature"]

    def test_rtl_text(self):
        case = make_case(failure_signature="مرحبا بالعالم - test signature")
        redacted, result = redact_case(case)
        # RTL text should not cause issues
        assert "مرحبا" in redacted["failure_signature"]

    def test_nested_deep_path(self):
        """Deeply nested Unix path."""
        case = make_case(failure_signature="Error in /a/b/c/d/e/f/g/h/config.json")
        redacted, result = redact_case(case)
        assert "/a/b/c/d/e/f" not in redacted["failure_signature"]


# ── Strict Mode ──

class TestStrictMode:
    def test_strict_blocks_on_any_issue(self):
        case = make_case(failure_signature="user email: test@example.com")
        _, result = redact_case(case, strict=True)
        assert result.blocked

    def test_strict_allows_clean_case(self):
        case = make_case(failure_signature="Skill xlsx was wrong for markdown table")
        _, result = redact_case(case, strict=True)
        assert not result.blocked


# ── Too Many Issues Block ──

class TestTooManyIssues:
    def test_many_issues_blocked(self):
        """When more than 5 issues are found, case should be blocked."""
        case = make_case(
            failure_signature="Email test@example.com at https://evil.com/api key sk-abcdefghijklmnop1234567890 phone 555-123-4567 uuid a1b2c3d4-e5f6-7890-abcd-ef0000000000 path /a/b/c/d/e/f"
        )
        _, result = redact_case(case)
        assert result.blocked


# ── Environment Redaction ──

class TestEnvironmentRedaction:
    def test_context_note_redacted(self):
        case = make_case(environment={
            "model": "claude-sonnet-4-6",
            "os": "macos",
            "context_note": "Running on https://internal.company.com server"
        })
        redacted, result = redact_case(case)
        assert "internal.company.com" not in redacted["environment"]["context_note"]

    def test_model_and_os_not_redacted(self):
        case = make_case(environment={
            "model": "claude-sonnet-4-6",
            "os": "macos"
        })
        redacted, result = redact_case(case)
        assert redacted["environment"]["model"] == "claude-sonnet-4-6"
        assert redacted["environment"]["os"] == "macos"


# ── CLI Exit Codes ──

class TestCLIExitCodes:
    def test_clean_case_exit_0(self, tmp_path):
        case_file = tmp_path / "clean.json"
        case = make_case()
        case_file.write_text(json.dumps(case))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "redact.py"),
             "--input", str(case_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_sensitive_content_exit_1(self, tmp_path):
        case_file = tmp_path / "sensitive.json"
        case = make_case(failure_signature="Contact: test@example.com")
        case_file.write_text(json.dumps(case))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "redact.py"),
             "--input", str(case_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 1

    def test_too_sensitive_exit_2(self, tmp_path):
        case_file = tmp_path / "blocked.json"
        case = make_case(
            failure_signature="Email test@example.com URL https://x.com key sk-abcdefghijklmnop1234567890 phone 555-123-4567 uuid a1b2c3d4-e5f6-7890-abcd-ef1234567890 path /a/b/c/d/e/f"
        )
        case_file.write_text(json.dumps(case))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "redact.py"),
             "--input", str(case_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 2

    def test_invalid_json_exit_3(self, tmp_path):
        case_file = tmp_path / "invalid.json"
        case_file.write_text("not json {{{")

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "redact.py"),
             "--input", str(case_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 3

    def test_file_not_found_exit_3(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "redact.py"),
             "--input", "/nonexistent/path.json"],
            capture_output=True, text=True
        )
        assert result.returncode == 3
