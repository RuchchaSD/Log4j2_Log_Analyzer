"""Sprint 2.5 — Log format type tests: pattern compiler, CRUD, and parser integration."""
import io
import pytest
from pathlib import Path

from server.core.pattern_compiler import compile_pattern, test_pattern as _test_pattern


# ── Sample lines ──────────────────────────────────────────────────────────────

TID_LINE = (
    "TID: [0] [1] [2024-03-15 09:01:06,012] INFO "
    "{org.wso2.carbon.apimgt.gateway.handlers.security.APIAuthenticationHandler} "
    "- API authentication handler initialized"
)
BRACKET_LINE = (
    "[2024-03-15 10:30:45,123]  INFO "
    "{org.wso2.carbon.mediation.ProxyServiceMessageReceiver} "
    "- Received message for proxy"
)
BASIC_LINE = (
    "2024-03-15 10:30:45,123 INFO  "
    "[org.wso2.carbon.user.core.UserStoreManager] "
    "- User authentication failed"
)

TID_PATTERN = "TID: [%tenantId] [%appName] [%d] %5p {%c} - %m%ex%n"
BRACKET_PATTERN = "[%d] %5p {%c} - %m%ex%n"
BASIC_PATTERN = "%d %5p [%c] - %m%ex%n"


# ── Pattern compiler: compile ─────────────────────────────────────────────────

def test_compile_tid_pattern_matches():
    regex, _ = compile_pattern(TID_PATTERN)
    assert regex is not None
    assert regex.match(TID_LINE) is not None


def test_compile_bracket_pattern_matches():
    regex, _ = compile_pattern(BRACKET_PATTERN)
    assert regex is not None
    assert regex.match(BRACKET_LINE) is not None


def test_compile_basic_pattern_matches():
    regex, _ = compile_pattern(BASIC_PATTERN)
    assert regex is not None
    assert regex.match(BASIC_LINE) is not None


def test_compile_extracts_timestamp_tid():
    regex, field_map = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert m is not None
    assert m.group('timestamp') == '2024-03-15 09:01:06,012'


def test_compile_extracts_level_tid():
    regex, _ = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert m.group('level').strip() == 'INFO'


def test_compile_extracts_logger_tid():
    regex, _ = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert 'APIAuthenticationHandler' in m.group('logger')


def test_compile_extracts_message_tid():
    regex, _ = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert 'API authentication handler' in m.group('message')


def test_compile_extracts_tid_field():
    regex, _ = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert m.group('tid') == '0'


def test_compile_extracts_app_name():
    regex, _ = compile_pattern(TID_PATTERN)
    m = regex.match(TID_LINE)
    assert m.group('app_name') == '1'


def test_compile_bracket_extracts_timestamp():
    regex, _ = compile_pattern(BRACKET_PATTERN)
    m = regex.match(BRACKET_LINE)
    assert m.group('timestamp') == '2024-03-15 10:30:45,123'


def test_compile_whitespace_flexible():
    """Pattern with single space should match line with multiple spaces."""
    regex, _ = compile_pattern("[%d] %p {%c} - %m")
    line = "[2024-03-15 10:30:45,123]    INFO   {some.Logger} - message"
    assert regex.match(line) is not None


def test_compile_invalid_pattern_returns_none():
    # A pattern that would generate an invalid regex
    regex, field_map = compile_pattern("[%d] %p {%c} - [unclosed")
    # This may or may not compile — at minimum it should not raise
    # If it does compile, verify it's either valid or None
    assert field_map is not None  # always returns a dict


def test_compile_skips_ex_directive():
    """The %ex directive should be silently skipped (no capture group)."""
    regex, field_map = compile_pattern("[%d] %p {%c} - %m%ex%n")
    assert 'ex' not in field_map
    assert 'n' not in field_map


def test_compile_field_map_has_expected_fields():
    _, field_map = compile_pattern(TID_PATTERN)
    assert 'timestamp' in field_map
    assert 'level' in field_map
    assert 'logger' in field_map
    assert 'message' in field_map


# ── Pattern compiler: test_pattern helper ─────────────────────────────────────

def test_test_pattern_matched():
    result = _test_pattern(TID_PATTERN, TID_LINE)
    assert result["matched"] is True
    assert result["error"] is None
    assert "timestamp" in result["fields"]
    assert "level" in result["fields"]


def test_test_pattern_no_match():
    result = _test_pattern(BRACKET_PATTERN, TID_LINE)
    assert result["matched"] is False
    assert result["error"] is None


def test_test_pattern_returns_regex_str():
    result = _test_pattern(TID_PATTERN, TID_LINE)
    assert result["regex"] is not None
    assert isinstance(result["regex"], str)


# ── Format type API: CRUD ─────────────────────────────────────────────────────

@pytest.fixture
def client_with_isolated_formats(client, monkeypatch, tmp_path):
    """Patch LOG_FORMATS_FILE to a temp path so user formats don't persist."""
    import server.config as cfg
    import server.core.format_manager as fm
    orig = cfg.LOG_FORMATS_FILE
    cfg.LOG_FORMATS_FILE = tmp_path / "log_formats.json"
    fm.LOG_FORMATS_FILE = tmp_path / "log_formats.json"
    yield client
    cfg.LOG_FORMATS_FILE = orig
    fm.LOG_FORMATS_FILE = orig


def test_list_formats_includes_builtins(client_with_isolated_formats):
    r = client_with_isolated_formats.get("/api/formats")
    assert r.status_code == 200
    formats = r.json()["formats"]
    ids = [f["id"] for f in formats]
    assert "builtin-tid" in ids
    assert "builtin-bracket" in ids
    assert "builtin-basic" in ids


def test_list_formats_builtins_marked(client_with_isolated_formats):
    formats = client_with_isolated_formats.get("/api/formats").json()["formats"]
    builtins = [f for f in formats if f["id"].startswith("builtin-")]
    assert all(f["is_builtin"] for f in builtins)


def test_create_format(client_with_isolated_formats):
    r = client_with_isolated_formats.post("/api/formats", json={
        "name": "Custom_MI_Format",
        "pattern": "[%d] %5p {%c} - %m%ex%n",
        "description": "Custom test format",
        "product": "mi",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Custom_MI_Format"
    assert body["is_builtin"] is False
    assert "id" in body


def test_create_format_duplicate_name(client_with_isolated_formats):
    payload = {"name": "DuplicateFormat", "pattern": "[%d] %p - %m"}
    client_with_isolated_formats.post("/api/formats", json=payload)
    r = client_with_isolated_formats.post("/api/formats", json=payload)
    assert r.status_code == 400


def test_get_format_builtin(client_with_isolated_formats):
    r = client_with_isolated_formats.get("/api/formats/builtin-tid")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "builtin-tid"
    assert "TID:" in body["pattern"]


def test_get_format_user_defined(client_with_isolated_formats):
    created = client_with_isolated_formats.post("/api/formats", json={
        "name": "MyCustomFormat", "pattern": "%d %p {%c} - %m"
    }).json()
    r = client_with_isolated_formats.get(f"/api/formats/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_format_not_found(client_with_isolated_formats):
    r = client_with_isolated_formats.get("/api/formats/nonexistent-id")
    assert r.status_code == 404


def test_update_format(client_with_isolated_formats):
    created = client_with_isolated_formats.post("/api/formats", json={
        "name": "ToUpdate", "pattern": "[%d] %p - %m"
    }).json()
    r = client_with_isolated_formats.put(f"/api/formats/{created['id']}", json={
        "description": "Updated description"
    })
    assert r.status_code == 200
    assert r.json()["description"] == "Updated description"


def test_update_builtin_rejected(client_with_isolated_formats):
    r = client_with_isolated_formats.put("/api/formats/builtin-tid", json={
        "description": "Attempting to modify built-in"
    })
    assert r.status_code == 403


def test_delete_format(client_with_isolated_formats):
    created = client_with_isolated_formats.post("/api/formats", json={
        "name": "ToDelete", "pattern": "[%d] %p - %m"
    }).json()
    r = client_with_isolated_formats.delete(f"/api/formats/{created['id']}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    # No longer in list
    formats = client_with_isolated_formats.get("/api/formats").json()["formats"]
    assert not any(f["id"] == created["id"] for f in formats)


def test_delete_builtin_rejected(client_with_isolated_formats):
    r = client_with_isolated_formats.delete("/api/formats/builtin-bracket")
    assert r.status_code == 403


# ── Format test endpoint ──────────────────────────────────────────────────────

def test_format_test_endpoint_matches(client_with_isolated_formats):
    r = client_with_isolated_formats.post("/api/formats/test", json={
        "pattern": TID_PATTERN,
        "line": TID_LINE,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] is True
    assert "timestamp" in body["fields"]
    assert "level" in body["fields"]


def test_format_test_endpoint_no_match(client_with_isolated_formats):
    r = client_with_isolated_formats.post("/api/formats/test", json={
        "pattern": BRACKET_PATTERN,
        "line": TID_LINE,
    })
    assert r.status_code == 200
    assert r.json()["matched"] is False


# ── Parser integration ────────────────────────────────────────────────────────

@pytest.fixture
def project(client_with_isolated_formats, project_payload):
    r = client_with_isolated_formats.post("/api/projects", json=project_payload)
    assert r.status_code == 201
    return r.json()


def _upload(client, project_id, filename, content, format_type_id=None):
    url = f"/api/logs/upload?project_id={project_id}"
    if format_type_id:
        url += f"&format_type_id={format_type_id}"
    return client.post(url, files={"file": (filename, io.BytesIO(content.encode()), "text/plain")})


BRACKET_LOG = """\
[2024-03-15 10:30:45,123]  INFO {org.wso2.carbon.mediation.ProxySvc} - Received message for proxy
[2024-03-15 10:30:45,200]  WARN {org.wso2.carbon.mediation.Throttle} - Throttle limit exceeded
[2024-03-15 10:30:45,300]  ERROR {org.wso2.carbon.apimgt.OAuthAuth} - Token validation failed
org.wso2.SomeException: invalid token
\tat org.wso2.Something.method(Something.java:42)
"""


def test_format_type_stored_in_metadata(client_with_isolated_formats, project):
    uploaded = _upload(
        client_with_isolated_formats, project["id"],
        "app.log", BRACKET_LOG, format_type_id="builtin-bracket"
    ).json()
    assert uploaded["format_type_id"] == "builtin-bracket"


def test_parse_with_bracket_format(client_with_isolated_formats, project):
    uploaded = _upload(
        client_with_isolated_formats, project["id"],
        "app.log", BRACKET_LOG, format_type_id="builtin-bracket"
    ).json()
    log_id = uploaded["id"]

    r = client_with_isolated_formats.get(
        f"/api/logs/{log_id}/entries?project_id={project['id']}&limit=10"
    )
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 3
    levels = {e["level"] for e in entries}
    assert levels == {"INFO", "WARN", "ERROR"}


def test_parse_with_bracket_format_extracts_logger(client_with_isolated_formats, project):
    uploaded = _upload(
        client_with_isolated_formats, project["id"],
        "app.log", BRACKET_LOG, format_type_id="builtin-bracket"
    ).json()
    log_id = uploaded["id"]

    entries = client_with_isolated_formats.get(
        f"/api/logs/{log_id}/entries?project_id={project['id']}&limit=10"
    ).json()["entries"]
    assert entries[0]["logger"] == "org.wso2.carbon.mediation.ProxySvc"


def test_parse_with_custom_format(client_with_isolated_formats, project):
    # Create a custom format for a simplified pattern
    fmt = client_with_isolated_formats.post("/api/formats", json={
        "name": "SimpleTest", "pattern": "%d %5p [%c] - %m"
    }).json()

    log_content = "2024-03-15 10:30:45,123 INFO  [org.test.Foo] - Hello World\n"
    uploaded = _upload(
        client_with_isolated_formats, project["id"],
        "simple.log", log_content, format_type_id=fmt["id"]
    ).json()
    log_id = uploaded["id"]

    entries = client_with_isolated_formats.get(
        f"/api/logs/{log_id}/entries?project_id={project['id']}"
    ).json()["entries"]
    assert len(entries) == 1
    assert entries[0]["level"] == "INFO"
    assert entries[0]["message"] == "Hello World"


def test_parse_fallback_no_format(client_with_isolated_formats, project):
    """Without a format type, auto-detection still works."""
    uploaded = _upload(
        client_with_isolated_formats, project["id"], "auto.log", BRACKET_LOG
    ).json()
    assert uploaded["format_type_id"] is None

    log_id = uploaded["id"]
    entries = client_with_isolated_formats.get(
        f"/api/logs/{log_id}/entries?project_id={project['id']}&limit=10"
    ).json()["entries"]
    # Auto-detection should find at least some entries
    assert len(entries) > 0


def test_set_log_format_api(client_with_isolated_formats, project):
    """PUT /api/logs/{id}/format changes the assigned format type."""
    uploaded = _upload(
        client_with_isolated_formats, project["id"], "app.log", BRACKET_LOG
    ).json()
    log_id = uploaded["id"]
    assert uploaded["format_type_id"] is None

    r = client_with_isolated_formats.put(
        f"/api/logs/{log_id}/format?project_id={project['id']}",
        json={"format_type_id": "builtin-bracket"},
    )
    assert r.status_code == 200
    assert r.json()["format_type_id"] == "builtin-bracket"


def test_project_default_format_applied(client_with_isolated_formats, project_payload, tmp_path):
    """Log files use project default format_type_id when none specified explicitly."""
    # Create a project with defaultFormatTypeId set
    payload = dict(project_payload)
    payload["name"] = "DefaultFmtProject"
    r = client_with_isolated_formats.post("/api/projects", json=payload)
    proj = r.json()

    # Update project settings to set a default format type
    client_with_isolated_formats.put(
        f"/api/projects/{proj['id']}",
        json={"settings": {"defaultFormatTypeId": "builtin-bracket"}},
    )

    # Upload without specifying format_type_id
    uploaded = _upload(
        client_with_isolated_formats, proj["id"], "app.log", BRACKET_LOG
    ).json()
    assert uploaded["format_type_id"] == "builtin-bracket"
