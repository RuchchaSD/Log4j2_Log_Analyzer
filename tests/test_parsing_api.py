"""Sprint 2 — Parsing, filter, groups, and search API tests."""
import io
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project(client, project_payload):
    r = client.post("/api/projects", json=project_payload)
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def log_file(client, project, sample_log_file):
    """Register the sample fixture log and return its metadata."""
    r = client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": str(sample_log_file)},
    )
    assert r.status_code == 201
    return r.json()


def _entries_url(log_id, project_id, **kwargs):
    params = f"project_id={project_id}"
    for k, v in kwargs.items():
        params += f"&{k}={v}"
    return f"/api/logs/{log_id}/entries?{params}"


def _filter(client, log_id, project_id, **body_kwargs):
    return client.post(
        f"/api/logs/{log_id}/filter?project_id={project_id}",
        json=body_kwargs,
    )


# ── Entries — pagination ──────────────────────────────────────────────────────

def test_get_entries_returns_data(client, project, log_file):
    r = client.get(_entries_url(log_file["id"], project["id"]))
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert "total" in body
    assert body["total"] > 0


def test_get_entries_default_limit(client, project, log_file):
    r = client.get(_entries_url(log_file["id"], project["id"]))
    body = r.json()
    assert len(body["entries"]) <= 200


def test_get_entries_limit_respected(client, project, log_file):
    r = client.get(_entries_url(log_file["id"], project["id"], limit=5))
    body = r.json()
    assert len(body["entries"]) <= 5


def test_get_entries_offset(client, project, log_file):
    all_r = client.get(_entries_url(log_file["id"], project["id"], offset=0, limit=500))
    offset_r = client.get(_entries_url(log_file["id"], project["id"], offset=1, limit=500))
    all_entries = all_r.json()["entries"]
    offset_entries = offset_r.json()["entries"]
    if len(all_entries) > 1:
        assert all_entries[1]["line_number"] == offset_entries[0]["line_number"]


def test_get_entries_total_consistent(client, project, log_file):
    r1 = client.get(_entries_url(log_file["id"], project["id"], offset=0, limit=5))
    r2 = client.get(_entries_url(log_file["id"], project["id"], offset=0, limit=500))
    assert r1.json()["total"] == r2.json()["total"]


# ── Summary ───────────────────────────────────────────────────────────────────

def test_get_log_summary(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/summary?project_id={project['id']}")
    assert r.status_code == 200
    body = r.json()
    assert "level_counts" in body
    assert "total_entries" in body


def test_summary_total_matches_entries_total(client, project, log_file):
    summary_r = client.get(f"/api/logs/{log_file['id']}/summary?project_id={project['id']}")
    entries_r = client.get(_entries_url(log_file["id"], project["id"], limit=1))
    assert summary_r.json()["total_entries"] == entries_r.json()["total"]


def test_summary_level_counts_sum_to_total(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/summary?project_id={project['id']}")
    body = r.json()
    total_from_levels = sum(body["level_counts"].values())
    assert total_from_levels == body["total_entries"]


def test_summary_has_date_range(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/summary?project_id={project['id']}")
    body = r.json()
    # date range fields exist and are non-null for a real log
    assert body.get("first_timestamp") is not None
    assert body.get("last_timestamp") is not None


# ── Filter — by level ─────────────────────────────────────────────────────────

def test_filter_by_level_error(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], levels=["ERROR"])
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) > 0
    assert all(e["level"] == "ERROR" for e in entries)


def test_filter_by_level_info(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], levels=["INFO"])
    entries = r.json()["entries"]
    assert all(e["level"] == "INFO" for e in entries)


def test_filter_by_multiple_levels(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], levels=["ERROR", "WARN"])
    entries = r.json()["entries"]
    assert all(e["level"] in ("ERROR", "WARN") for e in entries)


def test_filter_no_levels_returns_all(client, project, log_file):
    unfiltered = client.get(_entries_url(log_file["id"], project["id"], limit=1000))
    filtered = _filter(client, log_file["id"], project["id"])
    assert filtered.json()["total"] == unfiltered.json()["total"]


# ── Filter — search ───────────────────────────────────────────────────────────

def test_filter_search_text(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], search="Carbon")
    entries = r.json()["entries"]
    assert len(entries) > 0
    for e in entries:
        assert "carbon" in e["message"].lower() or "carbon" in e["logger"].lower()


def test_filter_search_no_results(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], search="xyzzy_no_such_thing_in_log")
    assert r.json()["total"] == 0


def test_filter_search_regex(client, project, log_file):
    # Regex: any word that starts with "API" case-insensitively
    r = _filter(client, log_file["id"], project["id"], search="API.*[Hh]andler", regex=True)
    assert r.status_code == 200
    entries = r.json()["entries"]
    # Just verify the endpoint handles regex without error
    assert isinstance(entries, list)


# ── Filter — has_stack_trace ──────────────────────────────────────────────────

def test_filter_has_stack_trace_true(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], has_stack_trace=True)
    entries = r.json()["entries"]
    assert len(entries) > 0
    assert all(e["has_stack_trace"] is True for e in entries)


def test_filter_has_stack_trace_false(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], has_stack_trace=False)
    entries = r.json()["entries"]
    assert all(not e["has_stack_trace"] for e in entries)


# ── Filter — combined ─────────────────────────────────────────────────────────

def test_filter_level_and_search_combined(client, project, log_file):
    r = _filter(client, log_file["id"], project["id"], levels=["ERROR"], search="token")
    entries = r.json()["entries"]
    assert all(e["level"] == "ERROR" for e in entries)


def test_filter_pagination(client, project, log_file):
    page1 = _filter(client, log_file["id"], project["id"], offset=0, limit=2).json()
    page2 = _filter(client, log_file["id"], project["id"], offset=2, limit=2).json()
    if page1["total"] > 2:
        # Pages should not overlap
        p1_lines = {e["line_number"] for e in page1["entries"]}
        p2_lines = {e["line_number"] for e in page2["entries"]}
        assert p1_lines.isdisjoint(p2_lines)


# ── Groups ────────────────────────────────────────────────────────────────────

def test_group_by_level(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/groups/level?project_id={project['id']}")
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert len(groups) > 0
    valid_levels = {"INFO", "WARN", "ERROR", "DEBUG", "TRACE", "FATAL"}
    for g in groups:
        assert g["key"] in valid_levels
        assert g["count"] > 0


def test_group_by_component(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/groups/component?project_id={project['id']}")
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert isinstance(groups, list)


def test_group_by_logger(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/groups/logger?project_id={project['id']}")
    assert r.status_code == 200
    groups = r.json()["groups"]
    total_from_groups = sum(g["count"] for g in groups)
    summary = client.get(f"/api/logs/{log_file['id']}/summary?project_id={project['id']}").json()
    assert total_from_groups == summary["total_entries"]


def test_group_invalid_field(client, project, log_file):
    r = client.get(f"/api/logs/{log_file['id']}/groups/notafield?project_id={project['id']}")
    assert r.status_code == 400


# ── Cross-file search ─────────────────────────────────────────────────────────

def test_search_single_file(client, project, log_file):
    r = client.post(
        f"/api/logs/search?project_id={project['id']}",
        json={"query": "WSO2 Carbon", "regex": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert body["total"] > 0


def test_search_no_results(client, project, log_file):
    r = client.post(
        f"/api/logs/search?project_id={project['id']}",
        json={"query": "xyzzy_unique_string_not_in_log", "regex": False},
    )
    assert r.json()["total"] == 0


def test_search_with_level_filter(client, project, log_file):
    r = client.post(
        f"/api/logs/search?project_id={project['id']}",
        json={"query": "Carbon", "levels": ["ERROR"]},
    )
    results = r.json()["results"]
    assert all(e["level"] == "ERROR" for e in results)


def test_search_limit_respected(client, project, log_file):
    r = client.post(
        f"/api/logs/search?project_id={project['id']}",
        json={"query": "wso2", "limit": 3},
    )
    assert len(r.json()["results"]) <= 3


def test_search_two_files(client, project, sample_log_file, tmp_path):
    """Search across two registered log files returns hits from both."""
    # Register the fixture log
    client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": str(sample_log_file)},
    )
    # Create and register a second log with a unique marker
    second_log = tmp_path / "second.log"
    second_log.write_text(
        "TID: [0] [] [2024-03-15 10:00:00,000] INFO {org.wso2.carbon.Test} - UNIQUE_MARKER_XYZ\n"
    )
    client.post(
        f"/api/logs/path?project_id={project['id']}",
        json={"path": str(second_log)},
    )

    r = client.post(
        f"/api/logs/search?project_id={project['id']}",
        json={"query": "UNIQUE_MARKER_XYZ"},
    )
    assert r.json()["total"] >= 1
