import json
import re
from pathlib import Path
from typing import Optional
from server.config import REPOS_SEED_FILE, JAR_OVERRIDES_SEED_FILE, FEATURES_SEED_FILE


_repo_map: Optional[dict[str, str]] = None
_jar_overrides: Optional[dict[str, str]] = None
_features: Optional[dict[str, list[str]]] = None


def _load_repo_map() -> dict[str, str]:
    global _repo_map
    if _repo_map is None:
        with open(REPOS_SEED_FILE) as f:
            _repo_map = json.load(f)
    return _repo_map


def _load_jar_overrides() -> dict[str, str]:
    global _jar_overrides
    if _jar_overrides is None:
        try:
            with open(JAR_OVERRIDES_SEED_FILE) as f:
                _jar_overrides = json.load(f)
        except FileNotFoundError:
            _jar_overrides = {}
    return _jar_overrides


def _load_features() -> dict[str, list[str]]:
    global _features
    if _features is None:
        try:
            with open(FEATURES_SEED_FILE) as f:
                _features = json.load(f)
        except FileNotFoundError:
            _features = {}
    return _features


def resolve_repo(package_name: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve a Java package to (repo_name, matched_prefix) via longest-prefix match."""
    pkg = package_name.strip()
    repos = _load_repo_map()

    if pkg in repos:
        return repos[pkg], pkg

    best_key = ""
    best_repo: Optional[str] = None
    for key, repo in repos.items():
        if pkg.startswith(key) and len(key) > len(best_key):
            best_key = key
            best_repo = repo

    if best_repo is None:
        return None, None
    return best_repo, best_key


def resolve_packages_for_repo(repo_name: str) -> list[str]:
    repos = _load_repo_map()
    return [pkg for pkg, r in repos.items() if r == repo_name]


def list_features() -> dict[str, list[str]]:
    return dict(_load_features())


# Mirrors cre-ai-agent's JAR_FILENAME_REGEX in jar-scanner.ts
_JAR_FILENAME_RE = re.compile(
    r"^(.+?)[-_](\d[\d.]*(?:[A-Za-z][A-Za-z0-9.]*)?)(?:_(\d+))?\.jar$"
)


def scan_jars(product_dir: str | Path) -> dict[str, str]:
    """Walk a WSO2 pack and return {artifactId: version} for every .jar found."""
    product_dir = Path(product_dir)
    jar_map: dict[str, str] = {}
    if not product_dir.exists():
        return jar_map

    for jar in product_dir.rglob("*.jar"):
        match = _JAR_FILENAME_RE.match(jar.name)
        if not match:
            continue
        artifact_id = match.group(1)
        base_version = match.group(2)
        patch = match.group(3)
        version = f"{base_version}.{patch}" if patch else base_version
        # First occurrence wins (mirrors cre-ai-agent behavior)
        jar_map.setdefault(artifact_id, version)
    return jar_map


def resolve_version_for_package(
    package_name: str, jar_map: dict[str, str]
) -> Optional[tuple[str, str]]:
    """Return (artifactId, version) for a package using jar-overrides and fuzzy match."""
    overrides = _load_jar_overrides()
    pkg = package_name

    if pkg in overrides:
        artifact_id = overrides[pkg]
        if artifact_id in jar_map:
            return artifact_id, jar_map[artifact_id]

    best_key = ""
    best_artifact: Optional[str] = None
    for prefix, artifact_id in overrides.items():
        if pkg.startswith(prefix) and len(prefix) > len(best_key):
            best_key = prefix
            best_artifact = artifact_id
    if best_artifact and best_artifact in jar_map:
        return best_artifact, jar_map[best_artifact]

    pkg_lower = pkg.lower()
    best_match: Optional[tuple[str, str]] = None
    best_len = 0
    for artifact_id, version in jar_map.items():
        if artifact_id.lower() in pkg_lower and len(artifact_id) > best_len:
            best_len = len(artifact_id)
            best_match = (artifact_id, version)
    return best_match


def _reset_caches() -> None:
    """Test helper: clear cached seed data."""
    global _repo_map, _jar_overrides, _features
    _repo_map = None
    _jar_overrides = None
    _features = None
