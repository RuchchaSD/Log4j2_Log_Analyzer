"""Tests for repo_resolver: package→repo mapping, JAR scan, version resolution."""
from pathlib import Path
import pytest
from server.core import repo_resolver


@pytest.fixture(autouse=True)
def reset_caches():
    repo_resolver._reset_caches()
    yield
    repo_resolver._reset_caches()


def test_repos_seed_loads():
    repos = repo_resolver._load_repo_map()
    assert isinstance(repos, dict)
    assert len(repos) > 0
    # Spot-check known WSO2 prefixes are present
    assert any(k.startswith("org.wso2.carbon.identity.oauth") for k in repos)


def test_exact_match_resolves():
    repo, prefix = repo_resolver.resolve_repo("org.wso2.carbon.identity.oauth")
    assert repo is not None
    assert prefix == "org.wso2.carbon.identity.oauth"


def test_longest_prefix_match():
    # endpoint sub-package should still resolve to the identity.oauth repo
    repo, prefix = repo_resolver.resolve_repo(
        "org.wso2.carbon.identity.oauth.endpoint.token"
    )
    assert repo is not None
    assert prefix is not None
    assert "org.wso2.carbon.identity.oauth".startswith(prefix) or prefix.startswith(
        "org.wso2.carbon.identity.oauth"
    )


def test_unknown_package_returns_none():
    repo, prefix = repo_resolver.resolve_repo("com.example.random.package")
    assert repo is None
    assert prefix is None


def test_features_loaded():
    features = repo_resolver.list_features()
    assert isinstance(features, dict)
    assert len(features) > 0


def test_scan_jars_empty_dir(tmp_path):
    result = repo_resolver.scan_jars(tmp_path)
    assert result == {}


def test_scan_jars_parses_filenames(tmp_path):
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "org.wso2.carbon.kernel_4.9.1.jar").touch()
    (tmp_path / "components" / "org.wso2.carbon.identity.oauth-6.12.0.jar").touch()
    (tmp_path / "components" / "synapse-core_4.0.0.wso2v262_2.jar").touch()

    jar_map = repo_resolver.scan_jars(tmp_path)
    assert jar_map.get("org.wso2.carbon.kernel") == "4.9.1"
    assert jar_map.get("org.wso2.carbon.identity.oauth") == "6.12.0"
    assert jar_map.get("synapse-core") == "4.0.0.wso2v262.2"


def test_resolve_version_for_package_fuzzy():
    jar_map = {"org.wso2.carbon.identity.oauth": "6.12.0"}
    result = repo_resolver.resolve_version_for_package(
        "org.wso2.carbon.identity.oauth.endpoint", jar_map
    )
    assert result == ("org.wso2.carbon.identity.oauth", "6.12.0")


def test_resolve_version_for_unknown_package():
    result = repo_resolver.resolve_version_for_package("com.foo.bar", {"baz": "1.0"})
    assert result is None
