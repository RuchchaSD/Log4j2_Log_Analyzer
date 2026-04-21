"""Tests for /api/repos endpoints and the repo_registry module."""
import pytest
from pathlib import Path


@pytest.fixture
def tiny_java_repo(tmp_path):
    """Create a tiny repo layout with two Java classes."""
    root = tmp_path / "tiny-repo"
    src = root / "src" / "main" / "java" / "org" / "example" / "foo"
    src.mkdir(parents=True)
    (src / "Foo.java").write_text(
        "package org.example.foo;\n\npublic class Foo {\n"
        "    public void bar() {\n"
        "        int x = 1;\n"
        "    }\n"
        "}\n"
    )
    (src / "Inner.java").write_text(
        "package org.example.foo;\n\npublic class Inner {}\n"
    )
    return root


def test_register_repo(client, tiny_java_repo):
    response = client.post(
        "/api/repos",
        json={"label": "tiny", "path": str(tiny_java_repo)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "tiny"
    assert data["id"]
    assert Path(data["path"]).resolve() == tiny_java_repo.resolve()


def test_register_repo_invalid_path(client):
    response = client.post(
        "/api/repos",
        json={"label": "ghost", "path": "/nonexistent/path/xyz"},
    )
    assert response.status_code == 404


def test_list_repos(client, tiny_java_repo):
    client.post("/api/repos", json={"label": "tiny", "path": str(tiny_java_repo)})
    response = client.get("/api/repos")
    assert response.status_code == 200
    assert len(response.json()["repos"]) == 1


def test_delete_repo(client, tiny_java_repo):
    r = client.post("/api/repos", json={"label": "tiny", "path": str(tiny_java_repo)})
    repo_id = r.json()["id"]
    response = client.delete(f"/api/repos/{repo_id}")
    assert response.status_code == 200
    response = client.get(f"/api/repos/{repo_id}/status")
    assert response.status_code == 404


def test_reindex_populates_counts(client, tiny_java_repo):
    r = client.post("/api/repos", json={"label": "tiny", "path": str(tiny_java_repo)})
    repo_id = r.json()["id"]
    response = client.post(f"/api/repos/{repo_id}/reindex")
    assert response.status_code == 200
    data = response.json()
    assert data["fileCount"] == 2
    assert data["classCount"] == 2

    status = client.get(f"/api/repos/{repo_id}/status").json()
    assert status["indexed"] is True


def test_resolve_endpoint(client):
    response = client.post(
        "/api/repos/resolve",
        json={"packageName": "org.wso2.carbon.identity.oauth.endpoint"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["repo"] is not None
    assert body["matchedPrefix"] is not None


def test_features_endpoint(client):
    response = client.get("/api/features")
    assert response.status_code == 200
    assert "features" in response.json()
    assert len(response.json()["features"]) > 0
