"""Sprint 2 — Log parser engine tests."""
import pytest
from pathlib import Path
from server.core.log_parser import detect_format, parse_log_file


# ── Sample line constants ─────────────────────────────────────────────────────

TID_LINE = "TID: [0] [1] [2024-03-15 09:01:06,012] INFO {org.wso2.carbon.apimgt.gateway.handlers.security.APIAuthenticationHandler} - API authentication handler initialized for tenant: carbon.super"
BRACKET_LINE = "[2024-03-15 10:30:45,123]  INFO - ProxyServiceMessageReceiver Received message for proxy"
BASIC_LINE = "2024-03-15 10:30:45,123 INFO  [org.wso2.carbon.user.core] - User authentication failed"

TID_ERROR_WITH_STACK = """\
TID: [0] [2] [2024-03-15 09:01:09,334] ERROR {org.wso2.carbon.apimgt.gateway.handlers.security.oauth.OAuthAuthenticator} - Error while validating token [abc123xyz]
org.wso2.carbon.apimgt.api.APIManagementException: Invalid consumer key : abc123xyz
\tat org.wso2.carbon.apimgt.keymgt.service.APIKeyValidationService.validateKey(APIKeyValidationService.java:112)
\tat org.wso2.carbon.apimgt.gateway.handlers.security.oauth.OAuthAuthenticator.authenticate(OAuthAuthenticator.java:289)
Caused by: java.lang.IllegalArgumentException: key not found
\tat com.example.Foo.bar(Foo.java:55)
"""


def _write_tmp_log(tmp_path, content, name="test.log"):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


# ── Format detection ──────────────────────────────────────────────────────────

def test_detect_format_tid():
    assert detect_format([TID_LINE]) == "tid"


def test_detect_format_bracket():
    assert detect_format([BRACKET_LINE]) == "bracket"


def test_detect_format_basic():
    assert detect_format([BASIC_LINE]) == "basic"


def test_detect_format_skips_blank_lines():
    assert detect_format(["", "  ", TID_LINE]) == "tid"


def test_detect_format_fallback():
    # Completely unrecognised lines → fallback to "tid"
    assert detect_format(["not a log line at all"]) == "tid"


# ── TID format parsing ────────────────────────────────────────────────────────

def test_parse_tid_entry_fields(tmp_path):
    path = _write_tmp_log(tmp_path, TID_LINE + "\n")
    entries = parse_log_file(path, "fid-1")
    assert len(entries) == 1
    e = entries[0]
    assert e.level == "INFO"
    assert e.logger == "org.wso2.carbon.apimgt.gateway.handlers.security.APIAuthenticationHandler"
    assert e.logger_short == "APIAuthenticationHandler"
    assert e.timestamp == "2024-03-15 09:01:06,012"
    assert e.timestamp_ms is not None
    assert e.tid == "0"
    assert e.app_name == "1"
    assert e.log_file_id == "fid-1"
    assert e.line_number == 1


def test_parse_tid_empty_tid_and_app(tmp_path):
    line = "TID: [] [] [2024-03-15 09:01:02,345] INFO {org.wso2.SomeClass} - Starting\n"
    path = _write_tmp_log(tmp_path, line)
    entries = parse_log_file(path, "fid")
    assert entries[0].tid is None
    assert entries[0].app_name is None


# ── Bracket format parsing ────────────────────────────────────────────────────

def test_parse_bracket_entry_fields(tmp_path):
    path = _write_tmp_log(tmp_path, BRACKET_LINE + "\n")
    entries = parse_log_file(path, "fid-2")
    assert len(entries) == 1
    e = entries[0]
    assert e.level == "INFO"
    assert e.logger == "ProxyServiceMessageReceiver"
    assert e.timestamp == "2024-03-15 10:30:45,123"
    assert e.log_file_id == "fid-2"


# ── Basic format parsing ──────────────────────────────────────────────────────

def test_parse_basic_entry_fields(tmp_path):
    path = _write_tmp_log(tmp_path, BASIC_LINE + "\n")
    entries = parse_log_file(path, "fid-3")
    assert len(entries) == 1
    e = entries[0]
    assert e.level == "INFO"
    assert e.logger == "org.wso2.carbon.user.core"
    assert e.message == "User authentication failed"


# ── Stack trace attachment ────────────────────────────────────────────────────

def test_stack_trace_attached(tmp_path):
    path = _write_tmp_log(tmp_path, TID_ERROR_WITH_STACK)
    entries = parse_log_file(path, "fid-4")
    # Only 1 log entry (not separate entries for stack lines)
    assert len(entries) == 1
    e = entries[0]
    assert e.has_stack_trace is True
    assert e.stack_trace is not None
    assert len(e.stack_trace) > 0


def test_caused_by_attached(tmp_path):
    path = _write_tmp_log(tmp_path, TID_ERROR_WITH_STACK)
    entries = parse_log_file(path, "fid-5")
    stack = entries[0].stack_trace
    assert any("Caused by:" in line for line in stack)


def test_stack_trace_not_double_counted(tmp_path):
    """Stack trace lines must NOT appear as separate LogEntry objects."""
    path = _write_tmp_log(tmp_path, TID_ERROR_WITH_STACK)
    entries = parse_log_file(path, "fid-6")
    # All entries with stack trace lines embedded → only 1 top-level entry
    assert all(e.level in {"INFO", "WARN", "ERROR", "DEBUG", "TRACE", "FATAL"}
               for e in entries)
    assert len(entries) == 1


def test_at_line_is_not_separate_entry(tmp_path):
    content = (
        "TID: [0] [] [2024-03-15 09:01:09,334] ERROR {org.wso2.Foo} - Something failed\n"
        "\tat org.wso2.Foo.method(Foo.java:10)\n"
        "TID: [0] [] [2024-03-15 09:01:10,000] INFO {org.wso2.Bar} - Next entry\n"
    )
    path = _write_tmp_log(tmp_path, content)
    entries = parse_log_file(path, "fid-7")
    assert len(entries) == 2
    assert entries[0].has_stack_trace is True
    assert entries[1].level == "INFO"


# ── Continuation lines ────────────────────────────────────────────────────────

def test_continuation_line_appended_to_message(tmp_path):
    content = (
        "TID: [0] [] [2024-03-15 09:01:02,345] INFO {org.wso2.SomeClass} - First line\n"
        "  continuation of the message\n"
        "TID: [0] [] [2024-03-15 09:01:03,000] INFO {org.wso2.Other} - Next entry\n"
    )
    path = _write_tmp_log(tmp_path, content)
    entries = parse_log_file(path, "fid-8")
    assert len(entries) == 2
    assert "continuation" in entries[0].message


# ── Line numbers ──────────────────────────────────────────────────────────────

def test_line_numbers_match_file_positions(tmp_path):
    content = (
        "TID: [0] [] [2024-03-15 09:01:02,001] INFO {A} - first\n"
        "TID: [0] [] [2024-03-15 09:01:02,002] INFO {B} - second\n"
        "TID: [0] [] [2024-03-15 09:01:02,003] INFO {C} - third\n"
    )
    path = _write_tmp_log(tmp_path, content)
    entries = parse_log_file(path, "fid-9")
    assert entries[0].line_number == 1
    assert entries[1].line_number == 2
    assert entries[2].line_number == 3


# ── logger_short ──────────────────────────────────────────────────────────────

def test_logger_short_extracted():
    from server.core.log_parser import _short_logger
    assert _short_logger("org.wso2.carbon.core.Foo") == "Foo"
    assert _short_logger("Foo") == "Foo"
    assert _short_logger("") == ""


# ── Real fixture log ──────────────────────────────────────────────────────────

def test_parse_sample_fixture(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    assert len(entries) > 0


def test_sample_fixture_has_info_entries(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    info_entries = [e for e in entries if e.level == "INFO"]
    assert len(info_entries) > 0


def test_sample_fixture_has_error_entries(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    error_entries = [e for e in entries if e.level == "ERROR"]
    assert len(error_entries) > 0


def test_sample_fixture_has_stack_traces(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    stacked = [e for e in entries if e.has_stack_trace]
    assert len(stacked) > 0


def test_sample_fixture_all_have_level(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    valid_levels = {"INFO", "WARN", "ERROR", "DEBUG", "TRACE", "FATAL"}
    for e in entries:
        assert e.level in valid_levels, f"Unexpected level: {e.level!r} at line {e.line_number}"


def test_sample_fixture_all_have_timestamp(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    for e in entries:
        assert e.timestamp is not None, f"Missing timestamp at line {e.line_number}"


def test_sample_fixture_line_numbers_unique(sample_log_file):
    entries = parse_log_file(str(sample_log_file), "fixture")
    line_nums = [e.line_number for e in entries]
    assert len(line_nums) == len(set(line_nums)), "Duplicate line numbers found"
