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
    """Override the home directory so analyzer state goes to a temp location."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    import server.config as cfg
    originals = {
        "RECENTS_FILE": cfg.RECENTS_FILE,
        "ANALYZER_HOME": cfg.ANALYZER_HOME,
        "REPOS_REGISTRY_FILE": cfg.REPOS_REGISTRY_FILE,
        "REPOS_CHECKOUT_DIR": cfg.REPOS_CHECKOUT_DIR,
        "LOG_FORMATS_FILE": cfg.LOG_FORMATS_FILE,
    }
    analyzer_home = fake_home / ".wso2analyzer"
    cfg.ANALYZER_HOME = analyzer_home
    cfg.RECENTS_FILE = analyzer_home / "recents.json"
    cfg.LOG_FORMATS_FILE = analyzer_home / "log_formats.json"
    cfg.REPOS_REGISTRY_FILE = analyzer_home / "repos.json"
    cfg.REPOS_CHECKOUT_DIR = analyzer_home / "repos"

    yield fake_home

    cfg.RECENTS_FILE = originals["RECENTS_FILE"]
    cfg.ANALYZER_HOME = originals["ANALYZER_HOME"]
    cfg.REPOS_REGISTRY_FILE = originals["REPOS_REGISTRY_FILE"]
    cfg.REPOS_CHECKOUT_DIR = originals["REPOS_CHECKOUT_DIR"]
    cfg.LOG_FORMATS_FILE = originals["LOG_FORMATS_FILE"]


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
