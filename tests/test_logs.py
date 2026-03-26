"""Sprint 1 — Log ingestion API tests."""
import io
import pytest
from pathlib import Path


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project(client, project_payload):
    """Create a project and return its JSON body."""
    r = client.post("/api/projects", json=project_payload)
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def log_content():
    """Minimal TID-format log file content."""
    return (
        "TID: [0] [] [2024-03-15 09:01:02,345] INFO {org.wso2.carbon.core.CarbonCoreActivator} - Starting WSO2 Carbon...\n"
        "TID: [0] [] [2024-03-15 09:01:03,100] WARN {org.wso2.carbon.apimgt.impl.handlers.ScopesIssuer} - No scopes defined\n"
        "TID: [0] [] [2024-03-15 09:01:04,200] ERROR {org.wso2.carbon.apimgt.gateway.OAuthAuthenticator} - Token validation failed\n"
    )


def _upload(client, project_id, filename, content):
    return client.post(
        f"/api/logs/upload?project_id={project_id}",
        files={"file": (filename, io.BytesIO(content.encode()), "text/plain")},
    )


# ── Upload ────────────────────────────────────────────────────────────────────

def test_upload_log_file(client, project, log_content):
    r = _upload(client, project["id"], "wso2carbon.log", log_content)
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "wso2carbon.log"
    assert body["size_bytes"] > 0
    assert body["line_count"] == 3

    # File copied into project logs/ directory
    dest = Path(project["path"]) / "logs" / "wso2carbon.log"
    assert dest.exists()


def test_upload_log_file_project_not_found(client, log_content):
    r = _upload(client, "nonexistent-project-id", "test.log", log_content)
    assert r.status_code == 404


def test_upload_sets_file_type_wso2carbon(client, project, log_content):
    r = _upload(client, project["id"], "wso2carbon.log", log_content)
    assert r.json()["file_type"] == "wso2carbon"


def test_upload_sets_file_type_audit(client, project, log_content):
    r = _upload(client, project["id"], "audit.log", log_content)
    assert r.json()["file_type"] == "audit"


def test_upload_sets_file_type_http_access(client, project, log_content):
    r = _upload(client, project["id"], "http_access_2024.log", log_content)
    assert r.json()["file_type"] == "http_access"


def test_upload_sets_file_type_correlation(client, project, log_content):
    r = _upload(client, project["id"], "correlation.log", log_content)
    assert r.json()["file_type"] == "correlation"


def test_upload_sets_file_type_generic(client, project, log_content):
    r = _upload(client, project["id"], "something_else.log", log_content)
    assert r.json()["file_type"] == "generic"


def test_upload_is_reference_false(client, project, log_content):
    r = _upload(client, project["id"], "wso2carbon.log", log_content)
    assert r.json()["is_reference"] is False


# ── Register path ─────────────────────────────────────────────────────────────

def test_add_log_path(client, project, sample_log_file):
    r = client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": str(sample_log_file)},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["is_reference"] is True
    assert body["filename"] == sample_log_file.name
    assert body["line_count"] is not None
    assert body["line_count"] > 0


def test_add_log_path_not_found(client, project):
    r = client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": "/nonexistent/path/wso2carbon.log"},
    )
    assert r.status_code == 404


def test_add_log_path_missing_body(client, project):
    # Empty body: path field is empty string → 400 (business validation)
    # Completely absent path key → 422 (Pydantic validation)
    r = client.post(f"/api/logs/path?project_id={project['id']}", json={})
    assert r.status_code in (400, 422)


# ── Register folder ───────────────────────────────────────────────────────────

def test_add_log_folder(client, project, tmp_path):
    # Create a folder with two log files and one txt file
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "app1.log").write_text("TID: [0] [] [2024-03-15 09:01:02,345] INFO {A} - msg\n")
    (log_dir / "app2.log").write_text("TID: [0] [] [2024-03-15 09:01:02,346] INFO {B} - msg\n")
    (log_dir / "readme.txt").write_text("not a log\n")
    (log_dir / "data.csv").write_text("col1,col2\n")  # should be ignored

    r = client.post(
        f"/api/logs/folder?project_id={project['id']}",
        json={"folder": str(log_dir)},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["added"] == 3  # .log + .txt files


def test_add_log_folder_skips_duplicates(client, project, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "app1.log").write_text("TID: [0] [] [2024-03-15 09:01:02,345] INFO {A} - msg\n")

    client.post(f"/api/logs/folder?project_id={project['id']}", json={"folder": str(log_dir)})
    r2 = client.post(f"/api/logs/folder?project_id={project['id']}", json={"folder": str(log_dir)})
    assert r2.json()["added"] == 0  # already registered, no duplicates


def test_add_log_folder_not_found(client, project):
    r = client.post(
        f"/api/logs/folder?project_id={project['id']}",
        json={"folder": "/nonexistent/folder"},
    )
    assert r.status_code == 404


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_logs_empty(client, project):
    r = client.get(f"/api/logs?project_id={project['id']}")
    assert r.status_code == 200
    assert r.json()["logs"] == []


def test_list_logs_after_upload(client, project, log_content):
    _upload(client, project["id"], "wso2carbon.log", log_content)
    r = client.get(f"/api/logs?project_id={project['id']}")
    logs = r.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["filename"] == "wso2carbon.log"


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_log(client, project, log_content):
    uploaded = _upload(client, project["id"], "wso2carbon.log", log_content).json()
    log_id = uploaded["id"]

    r = client.delete(f"/api/logs/{log_id}?project_id={project['id']}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # No longer in list
    logs = client.get(f"/api/logs?project_id={project['id']}").json()["logs"]
    assert not any(l["id"] == log_id for l in logs)


def test_delete_log_not_found(client, project):
    r = client.delete(f"/api/logs/nonexistent-log-id?project_id={project['id']}")
    assert r.status_code == 404


# ── Metadata extraction ───────────────────────────────────────────────────────

def test_metadata_extraction_from_sample(client, project, sample_log_file):
    r = client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": str(sample_log_file)},
    )
    body = r.json()
    assert body["size_bytes"] > 0
    assert body["line_count"] is not None and body["line_count"] > 0
    assert body["first_timestamp"] is not None
    assert body["last_timestamp"] is not None
    # first timestamp should be before (or equal to) last timestamp
    assert body["first_timestamp"] <= body["last_timestamp"]
