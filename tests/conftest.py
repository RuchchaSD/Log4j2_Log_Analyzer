"""Pytest configuration and shared fixtures for WSO2 Log Analyzer tests."""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def sample_log_file():
    """Path to the sample WSO2 Carbon log fixture."""
    return Path(__file__).parent / "fixtures" / "sample_wso2carbon.log"


@pytest.fixture
def temp_dir():
    """Create a temporary directory for each test, cleaned up afterwards."""
    d = tempfile.mkdtemp(prefix="wso2test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Override the home directory so recents.json goes to a temp location."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Patch Path.home() to return our fake home
    import server.config as cfg
    original_recents = cfg.RECENTS_FILE
    cfg.RECENTS_FILE = fake_home / ".wso2analyzer" / "recents.json"

    yield fake_home

    cfg.RECENTS_FILE = original_recents


@pytest.fixture
def client(temp_home):
    """FastAPI test client with isolated home directory."""
    from server.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def project_payload(temp_dir):
    """A valid project creation payload pointing at a temp directory."""
    return {
        "name": "TestProject",
        "product": "apim",
        "productVersion": "4.3.0",
        "path": str(temp_dir),
        "u2Level": "WUM-10",
        "installPath": None,
    }
