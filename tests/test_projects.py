"""Sprint 1 — Project CRUD API tests."""
import json
import pytest
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create(client, payload):
    return client.post("/api/projects", json=payload)


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_project(client, project_payload):
    r = _create(client, project_payload)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == project_payload["name"]
    assert body["product"] == project_payload["product"]
    assert "id" in body

    # Folder structure created on disk
    project_dir = Path(body["path"])
    assert project_dir.exists()
    assert (project_dir / ".wso2analyzer" / "project.json").exists()
    assert (project_dir / "logs").exists()
    assert (project_dir / "reports").exists()


def test_create_project_missing_name(client, project_payload):
    bad = dict(project_payload)
    del bad["name"]
    r = _create(client, bad)
    assert r.status_code == 422


def test_create_project_missing_product(client, project_payload):
    bad = dict(project_payload)
    del bad["product"]
    r = _create(client, bad)
    assert r.status_code == 422


def test_create_project_writes_project_json(client, project_payload):
    r = _create(client, project_payload)
    assert r.status_code == 201
    body = r.json()
    project_file = Path(body["path"]) / ".wso2analyzer" / "project.json"
    data = json.loads(project_file.read_text())
    assert data["name"] == project_payload["name"]
    assert data["id"] == body["id"]


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_projects_empty(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert r.json()["projects"] == []


def test_list_projects_after_create(client, project_payload):
    _create(client, project_payload)
    r = client.get("/api/projects")
    assert r.status_code == 200
    projects = r.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == project_payload["name"]


def test_list_projects_multiple(client, project_payload, temp_dir):
    _create(client, project_payload)
    second = dict(project_payload)
    second["name"] = "SecondProject"
    second["path"] = str(temp_dir)
    _create(client, second)
    r = client.get("/api/projects")
    names = [p["name"] for p in r.json()["projects"]]
    assert "TestProject" in names
    assert "SecondProject" in names


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_project(client, project_payload):
    created = _create(client, project_payload).json()
    r = client.get(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert r.json()["name"] == project_payload["name"]


def test_get_project_not_found(client):
    r = client.get("/api/projects/nonexistent-id")
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_project_name(client, project_payload):
    created = _create(client, project_payload).json()
    r = client.put(f"/api/projects/{created['id']}", json={"name": "UpdatedName"})
    assert r.status_code == 200
    assert r.json()["name"] == "UpdatedName"


def test_update_project_persists_to_disk(client, project_payload):
    created = _create(client, project_payload).json()
    client.put(f"/api/projects/{created['id']}", json={"notes": "some notes"})
    project_file = Path(created["path"]) / ".wso2analyzer" / "project.json"
    data = json.loads(project_file.read_text())
    assert data["notes"] == "some notes"


def test_update_project_not_found(client):
    r = client.put("/api/projects/nonexistent-id", json={"name": "X"})
    assert r.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_project(client, project_payload):
    created = _create(client, project_payload).json()
    r = client.delete(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # .wso2analyzer folder removed
    analyzer_dir = Path(created["path"]) / ".wso2analyzer"
    assert not analyzer_dir.exists()

    # No longer in recents
    projects = client.get("/api/projects").json()["projects"]
    ids = [p["id"] for p in projects]
    assert created["id"] not in ids


def test_delete_project_not_found(client):
    r = client.delete("/api/projects/nonexistent-id")
    assert r.status_code == 404


# ── Open ──────────────────────────────────────────────────────────────────────

def test_open_project(client, project_payload):
    created = _create(client, project_payload).json()
    r = client.post("/api/projects/open", json={"path": created["path"]})
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_open_project_invalid_path(client):
    r = client.post("/api/projects/open", json={"path": "/nonexistent/path/that/does/not/exist"})
    assert r.status_code == 404


def test_open_project_missing_path(client):
    r = client.post("/api/projects/open", json={})
    assert r.status_code == 400
