"""Tests for stack trace parsing + resolution against registered repos."""
import pytest
from server.core import stack_trace


SAMPLE_TRACE = """java.lang.RuntimeException: boom
    at org.example.foo.Foo.bar(Foo.java:5)
    at org.example.foo.Foo$Inner.baz(Foo.java:12)
    at org.wso2.carbon.identity.oauth.OAuthService.revokeToken(OAuthService.java:142)
    at com.sun.proxy.$Proxy123.invoke(Unknown Source)
"""


def test_parse_stack_trace_extracts_frames():
    frames = stack_trace.parse_stack_trace(SAMPLE_TRACE)
    assert len(frames) >= 3
    f = frames[0]
    assert f.packageName == "org.example.foo"
    assert f.className == "Foo"
    assert f.methodName == "bar"
    assert f.fileName == "Foo.java"
    assert f.lineNumber == 5


def test_parse_handles_inner_class():
    frames = stack_trace.parse_stack_trace(SAMPLE_TRACE)
    inner = next(f for f in frames if "$Inner" in f.className)
    assert inner.className == "Foo$Inner"


def test_is_wso2_frame():
    frames = stack_trace.parse_stack_trace(SAMPLE_TRACE)
    wso2 = [f for f in frames if stack_trace.is_wso2_frame(f)]
    assert len(wso2) == 1
    assert wso2[0].packageName == "org.wso2.carbon.identity.oauth"


def test_resolve_non_wso2_frame_has_reason():
    frames = stack_trace.parse_stack_trace(
        "    at com.foo.Bar.baz(Bar.java:1)"
    )
    assert len(frames) == 1
    resolved = stack_trace.resolve_frame(frames[0])
    assert resolved.resolved is False
    assert resolved.reason == "non_wso2_frame"


def test_resolve_wso2_unregistered_repo(temp_home):
    """WSO2 frame with no registered repo should report class_not_found_in_registered_repos."""
    frames = stack_trace.parse_stack_trace(
        "    at org.wso2.carbon.identity.oauth.OAuthService.revokeToken(OAuthService.java:142)"
    )
    resolved = stack_trace.resolve_frame(frames[0])
    assert resolved.resolved is False
    assert resolved.reason in {
        "class_not_found_in_registered_repos",
        "no_repo_mapping",
    }


def test_resolve_against_registered_repo(client, tmp_path):
    """End-to-end: register tiny repo, resolve a frame from it."""
    # Create a tiny repo with org.wso2.test.Foo
    root = tmp_path / "repo"
    src = root / "src" / "main" / "java" / "org" / "wso2" / "test"
    src.mkdir(parents=True)
    foo = src / "Foo.java"
    foo.write_text(
        "package org.wso2.test;\n\npublic class Foo {\n"
        "    public void bar() {\n"
        "    }\n}\n"
    )

    # Seed repos.json mapping for this test
    from server.core import repo_resolver
    repo_resolver._reset_caches()
    repo_resolver._repo_map = {"org.wso2.test": "test-repo"}

    r = client.post("/api/repos", json={"label": "test-repo", "path": str(root)})
    client.post(f"/api/repos/{r.json()['id']}/reindex")

    response = client.post(
        "/api/stacktrace/resolve",
        json={"stackTrace": "    at org.wso2.test.Foo.bar(Foo.java:4)"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert body["resolvedCount"] == 1
    frame = body["frames"][0]
    assert frame["resolved"] is True
    assert frame["filePath"] == str(foo)
    assert frame["repoLabel"] == "test-repo"

    # Clean up module-level cache pollution
    repo_resolver._reset_caches()


def test_inner_class_resolves_to_outer_file(client, tmp_path):
    """Frame for Foo$Inner should resolve to Foo.java."""
    root = tmp_path / "repo"
    src = root / "src" / "main" / "java" / "org" / "wso2" / "inner"
    src.mkdir(parents=True)
    foo = src / "Foo.java"
    foo.write_text("package org.wso2.inner;\npublic class Foo {}\n")

    from server.core import repo_resolver
    repo_resolver._reset_caches()
    repo_resolver._repo_map = {"org.wso2.inner": "inner-repo"}

    r = client.post("/api/repos", json={"label": "inner-repo", "path": str(root)})
    client.post(f"/api/repos/{r.json()['id']}/reindex")

    response = client.post(
        "/api/stacktrace/resolve",
        json={"stackTrace": "    at org.wso2.inner.Foo$Nested.run(Foo.java:2)"},
    )
    body = response.json()
    assert body["resolvedCount"] == 1
    assert body["frames"][0]["filePath"] == str(foo)

    repo_resolver._reset_caches()


def test_callpath_endpoint(client, tmp_path):
    response = client.post(
        "/api/stacktrace/callpath",
        json={
            "stackTrace": "    at org.wso2.x.Foo.bar(Foo.java:1)\n"
                         "    at org.wso2.y.Bar.baz(Bar.java:2)"
        },
    )
    assert response.status_code == 200
    assert response.json()["totalCount"] == 2


def test_source_file_endpoint(client, tmp_path):
    java = tmp_path / "X.java"
    java.write_text("\n".join(f"line{i}" for i in range(1, 21)))

    response = client.get(
        "/api/files/source",
        params={"path": str(java), "line": 10, "context": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["targetLine"] == 10
    assert "line10" in body["content"]
    assert body["startLine"] == 8
    assert body["endLine"] == 12
