import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from server import config as cfg
from server.models.repo import Repo, RepoCreate
from server.core.repo_scanner import RepoIndex, build_index, save_index, load_index


def _index_dir() -> Path:
    override = globals().get("_INDEX_DIR")
    return override if override else cfg.ANALYZER_HOME / "repo_indexes"


def _index_file_for(repo_id: str) -> Path:
    return _index_dir() / f"{repo_id}.json"


def _load_all() -> list[Repo]:
    if not cfg.REPOS_REGISTRY_FILE.exists():
        return []
    try:
        with open(cfg.REPOS_REGISTRY_FILE) as f:
            data = json.load(f)
        return [Repo(**r) for r in data.get("repos", [])]
    except (json.JSONDecodeError, KeyError):
        return []


def _save_all(repos: list[Repo]) -> None:
    cfg.REPOS_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg.REPOS_REGISTRY_FILE, "w") as f:
        json.dump(
            {"repos": [json.loads(r.model_dump_json()) for r in repos]},
            f, indent=2, default=str,
        )


def list_repos() -> list[Repo]:
    return _load_all()


def get_repo(repo_id: str) -> Optional[Repo]:
    for r in _load_all():
        if r.id == repo_id:
            return r
    return None


def register_repo(data: RepoCreate) -> Repo:
    path = Path(data.path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Repo path does not exist: {data.path}")

    repos = _load_all()
    # Dedupe by path
    repos = [r for r in repos if Path(r.path).resolve() != path]

    repo = Repo(
        label=data.label,
        path=str(path),
        branch=data.branch,
        remoteUrl=data.remoteUrl,
    )
    repos.append(repo)
    _save_all(repos)
    return repo


def delete_repo(repo_id: str) -> bool:
    repos = _load_all()
    filtered = [r for r in repos if r.id != repo_id]
    if len(filtered) == len(repos):
        return False
    _save_all(filtered)
    # Remove cached index
    index_file = _index_file_for(repo_id)
    if index_file.exists():
        index_file.unlink()
    return True


def reindex_repo(repo_id: str) -> Optional[Repo]:
    repo = get_repo(repo_id)
    if repo is None:
        return None
    index = build_index(repo.path)
    save_index(index, _index_file_for(repo_id))

    repos = _load_all()
    for r in repos:
        if r.id == repo_id:
            r.fileCount = index.file_count
            r.classCount = index.class_count
            r.lastIndexed = datetime.utcnow()
    _save_all(repos)
    return get_repo(repo_id)


def get_index(repo_id: str) -> Optional[RepoIndex]:
    return load_index(_index_file_for(repo_id))
