"""
Sprint 2 bug fix tests.

Three bugs were fixed after the initial Sprint 2 implementation:

  Bug 1 — Virtual scroll momentum / scrollbar drag broken
      Root cause: spacer-div approach wiped innerHTML on every scroll event,
      destabilising browser scroll physics.
      Fix: absolute-positioning virtual scroll with stable total height.
      Backend impact: none. Frontend-only fix verified via browser automation.

  Bug 2 — Log entries invisible after scroll fix
      Root cause: _showLoading() was injecting "Parsing..." text into
      #log-scroll-inner, then wiping it (including rendered rows) on hide.
      Fix: dedicated #log-loading div outside the scroll container.
      Backend impact: none. Frontend-only fix.

  Bug 3 — Old logs persisting on project switch
      Root cause: setCurrentProject() didn't call LogViewer.reset().
      Additionally, in-flight _fetchAndAppend calls could complete after
      reset() and repopulate the viewer (race condition).
      Fix: (a) setCurrentProject calls LogViewer.reset(); (b) _generation
      counter invalidates stale in-flight fetches.
      Backend impact: the isolation between projects is enforced at the API
      layer — log IDs are scoped to their project.

The tests below verify the backend-side guarantees that make Bug 3 safe:
project isolation and index consistency.
"""
import io
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_project(client, base_payload, name_suffix="", path_override=None):
    payload = dict(base_payload)
    payload["name"] = base_payload["name"] + name_suffix
    if path_override:
        payload["path"] = str(path_override)
    r = client.post("/api/projects", json=payload)
    assert r.status_code == 201
    return r.json()


def _upload(client, project_id, filename, content):
    return client.post(
        f"/api/logs/upload?project_id={project_id}",
        files={"file": (filename, io.BytesIO(content.encode()), "text/plain")},
    )


_SAMPLE_LOG = (
    "TID: [0] [] [2024-03-15 09:01:02,345] INFO {org.wso2.carbon.core.Startup} - Starting WSO2 Carbon...\n"
    "TID: [0] [] [2024-03-15 09:01:03,100] WARN {org.wso2.carbon.apimgt.ScopesIssuer} - No scopes defined\n"
    "TID: [0] [] [2024-03-15 09:01:04,200] ERROR {org.wso2.carbon.apimgt.OAuthAuth} - Token validation failed\n"
    "org.wso2.SomeException: token invalid\n"
    "\tat org.wso2.SomeClass.method(SomeClass.java:42)\n"
)


# ── Bug 3 backend: project isolation ─────────────────────────────────────────

class TestProjectIsolation:
    """
    The generation counter in the frontend (Bug 3 fix) prevents stale fetches
    from repopulating the viewer after a project switch. The backend side of
    this contract is that a log ID registered under project A returns 404 when
    queried in the context of project B.
    """

    def test_log_id_scoped_to_owning_project(self, client, project_payload, temp_dir):
        """Log registered under project A returns 404 when queried with project B's ID."""
        proj_a = _make_project(client, project_payload, "_A")
        proj_b = _make_project(client, project_payload, "_B", path_override=temp_dir)

        # Upload log to project A
        uploaded = _upload(client, proj_a["id"], "wso2carbon.log", _SAMPLE_LOG).json()
        log_id = uploaded["id"]

        # Querying entries with project B's ID → 404
        r = client.get(f"/api/logs/{log_id}/entries?project_id={proj_b['id']}")
        assert r.status_code == 404

    def test_filter_scoped_to_owning_project(self, client, project_payload, temp_dir):
        """Filter endpoint also rejects log IDs from another project."""
        proj_a = _make_project(client, project_payload, "_A")
        proj_b = _make_project(client, project_payload, "_B", path_override=temp_dir)

        uploaded = _upload(client, proj_a["id"], "wso2carbon.log", _SAMPLE_LOG).json()
        log_id = uploaded["id"]

        r = client.post(
            f"/api/logs/{log_id}/filter?project_id={proj_b['id']}",
            json={"levels": ["ERROR"]},
        )
        assert r.status_code == 404

    def test_two_projects_have_independent_log_lists(self, client, project_payload, temp_dir):
        """Each project maintains its own log file list."""
        proj_a = _make_project(client, project_payload, "_A")
        proj_b = _make_project(client, project_payload, "_B", path_override=temp_dir)

        _upload(client, proj_a["id"], "wso2carbon.log", _SAMPLE_LOG)
        _upload(client, proj_b["id"], "wso2carbon.log", _SAMPLE_LOG)

        logs_a = client.get(f"/api/logs?project_id={proj_a['id']}").json()["logs"]
        logs_b = client.get(f"/api/logs?project_id={proj_b['id']}").json()["logs"]

        # Each has exactly one log
        assert len(logs_a) == 1
        assert len(logs_b) == 1
        # Different IDs
        assert logs_a[0]["id"] != logs_b[0]["id"]

    def test_delete_log_in_project_a_does_not_affect_project_b(self, client, project_payload, temp_dir):
        proj_a = _make_project(client, project_payload, "_A")
        proj_b = _make_project(client, project_payload, "_B", path_override=temp_dir)

        log_a = _upload(client, proj_a["id"], "app.log", _SAMPLE_LOG).json()
        _upload(client, proj_b["id"], "app.log", _SAMPLE_LOG)

        # Delete from project A
        client.delete(f"/api/logs/{log_a['id']}?project_id={proj_a['id']}")

        # Project B's log still present
        logs_b = client.get(f"/api/logs?project_id={proj_b['id']}").json()["logs"]
        assert len(logs_b) == 1


# ── Bug 3 backend: index consistency (stale fetch prevention) ─────────────────

class TestIndexConsistency:
    """
    The _generation counter prevents stale in-flight fetches from corrupting
    the viewer. The backend guarantee is that building the index for the same
    file multiple times always produces the same result.
    """

    def test_index_rebuild_returns_same_total(self, client, project_payload):
        """Fetching entries for the same log twice returns the same total."""
        proj = _make_project(client, project_payload, "_idx")
        uploaded = _upload(client, proj["id"], "wso2carbon.log", _SAMPLE_LOG).json()
        log_id = uploaded["id"]

        r1 = client.get(f"/api/logs/{log_id}/entries?project_id={proj['id']}&offset=0&limit=500")
        r2 = client.get(f"/api/logs/{log_id}/entries?project_id={proj['id']}&offset=0&limit=500")

        assert r1.json()["total"] == r2.json()["total"]

    def test_filter_rebuild_consistent(self, client, project_payload):
        """Filtering the same log twice returns the same count."""
        proj = _make_project(client, project_payload, "_filter")
        uploaded = _upload(client, proj["id"], "wso2carbon.log", _SAMPLE_LOG).json()
        log_id = uploaded["id"]

        def do_filter():
            return client.post(
                f"/api/logs/{log_id}/filter?project_id={proj['id']}",
                json={"levels": ["ERROR"]},
            ).json()["total"]

        assert do_filter() == do_filter()

    def test_summary_consistent(self, client, project_payload):
        """Summary total is stable across multiple calls."""
        proj = _make_project(client, project_payload, "_sum")
        uploaded = _upload(client, proj["id"], "wso2carbon.log", _SAMPLE_LOG).json()
        log_id = uploaded["id"]

        s1 = client.get(f"/api/logs/{log_id}/summary?project_id={proj['id']}").json()["total_entries"]
        s2 = client.get(f"/api/logs/{log_id}/summary?project_id={proj['id']}").json()["total_entries"]
        assert s1 == s2


# ── Bug 3 backend: known entry counts from sample fixture ─────────────────────

class TestSampleFixtureIntegrity:
    """
    Verifies that the sample fixture produces deterministic, expected results.
    This guards against regressions where project-switch or index corruption
    causes entries to disappear or be counted incorrectly.
    """

    def test_sample_fixture_error_count_nonzero(self, client, project_payload, sample_log_file):
        proj = _make_project(client, project_payload, "_fixture")
        r = client.post(
            f"/api/logs/path?project_id={proj['id']}",
            json={"path": str(sample_log_file)},
        )
        log_id = r.json()["id"]

        summary = client.get(
            f"/api/logs/{log_id}/summary?project_id={proj['id']}"
        ).json()
        assert summary["level_counts"].get("ERROR", 0) > 0

    def test_sample_fixture_total_stable_across_calls(self, client, project_payload, sample_log_file):
        proj = _make_project(client, project_payload, "_stable")
        r = client.post(
            f"/api/logs/path?project_id={proj['id']}",
            json={"path": str(sample_log_file)},
        )
        log_id = r.json()["id"]

        t1 = client.get(f"/api/logs/{log_id}/entries?project_id={proj['id']}&limit=1").json()["total"]
        t2 = client.get(f"/api/logs/{log_id}/entries?project_id={proj['id']}&limit=1").json()["total"]
        assert t1 == t2
        assert t1 > 0
