import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from server import config as cfg


PUBLIC_ORG_PRIORITY = ["wso2", "wso2-extensions"]
PATCH_ORG = "wso2-support"

_NO_PROMPT_ENV = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "echo",
}


@dataclass
class CheckoutResult:
    local_path: str
    org: str
    repo_name: str
    tag: str
    created: bool  # True if worktree was newly created


def _bare_repo_path(org: str, repo_name: str) -> Path:
    return cfg.REPOS_CHECKOUT_DIR / org / f"{repo_name}.git"


def _worktree_path(org: str, repo_name: str, tag: str) -> Path:
    safe_tag = re.sub(r"[^a-zA-Z0-9._-]", "_", tag)
    return cfg.REPOS_CHECKOUT_DIR / org / repo_name / "worktrees" / safe_tag


def _build_tag_candidates(tag: str) -> list[str]:
    base = tag[1:] if tag.startswith("v") else tag
    normalized = re.sub(r"(\d)\.wso2v", r"\1-wso2v", base)
    seen: list[str] = []
    for candidate in (f"v{base}", base, f"v{normalized}", normalized):
        if candidate not in seen:
            seen.append(candidate)
    return seen


def _evict_old_worktrees(org: str, repo_name: str) -> None:
    worktrees_dir = cfg.REPOS_CHECKOUT_DIR / org / repo_name / "worktrees"
    if not worktrees_dir.exists():
        return
    entries = []
    for entry in worktrees_dir.iterdir():
        if entry.is_dir():
            try:
                entries.append((entry.stat().st_mtime, entry))
            except OSError:
                pass
    if len(entries) <= cfg.MAX_WORKTREES_PER_REPO:
        return
    entries.sort(key=lambda e: e[0])
    for _, path in entries[: len(entries) - cfg.MAX_WORKTREES_PER_REPO]:
        shutil.rmtree(path, ignore_errors=True)


def _run_git(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=_NO_PROMPT_ENV,
        timeout=120,
    )


def _has_github_pat() -> bool:
    pat = os.environ.get("GITHUB_PAT")
    return bool(pat and not re.match(r"^\$\{.+\}$", pat))


def _clone_url(org: str, repo_name: str) -> str:
    pat = os.environ.get("GITHUB_PAT", "")
    if org == PATCH_ORG and _has_github_pat():
        return f"https://{pat}@github.com/{org}/{repo_name}.git"
    return f"https://github.com/{org}/{repo_name}.git"


def _clone_and_checkout(org: str, repo_name: str, tag: str) -> CheckoutResult:
    bare_path = _bare_repo_path(org, repo_name)
    wt_path = _worktree_path(org, repo_name, tag)

    if not bare_path.exists():
        bare_path.parent.mkdir(parents=True, exist_ok=True)
        result = _run_git(["clone", "--bare", _clone_url(org, repo_name), str(bare_path)])
        if result.returncode != 0:
            raise RuntimeError(f"Clone failed for {org}/{repo_name}: {result.stderr.strip()}")
    else:
        _run_git(["fetch", "--tags", "--prune"], cwd=bare_path)

    created = False
    if not wt_path.exists():
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        checked_out = False
        last_err = ""
        for candidate in _build_tag_candidates(tag):
            result = _run_git(
                ["worktree", "add", "--detach", str(wt_path), candidate],
                cwd=bare_path,
            )
            if result.returncode == 0:
                checked_out = True
                break
            last_err = result.stderr.strip()
        if not checked_out:
            shutil.rmtree(wt_path, ignore_errors=True)
            raise RuntimeError(
                f"Tag {tag} not found in {org}/{repo_name}. Candidates tried: "
                f"{_build_tag_candidates(tag)}. Last error: {last_err}"
            )
        _evict_old_worktrees(org, repo_name)
        created = True

    return CheckoutResult(
        local_path=str(wt_path),
        org=org,
        repo_name=repo_name,
        tag=tag,
        created=created,
    )


def ensure_worktree(repo_name: str, tag: str) -> CheckoutResult:
    """Ensure a worktree exists for {repo_name}@{tag}, cloning bare repo if needed.

    Search order: wso2, wso2-extensions, then wso2-support (if GITHUB_PAT set).
    """
    orgs = PUBLIC_ORG_PRIORITY + ([PATCH_ORG] if _has_github_pat() else [])

    # Fast path: already on disk under any org
    for org in orgs:
        wt = _worktree_path(org, repo_name, tag)
        if wt.exists():
            return CheckoutResult(
                local_path=str(wt),
                org=org,
                repo_name=repo_name,
                tag=tag,
                created=False,
            )

    last_err: Optional[Exception] = None
    for org in PUBLIC_ORG_PRIORITY:
        try:
            return _clone_and_checkout(org, repo_name, tag)
        except RuntimeError as err:
            last_err = err
            msg = str(err)
            if "Tag " in msg and "not found" in msg and _has_github_pat():
                try:
                    return _clone_and_checkout(PATCH_ORG, repo_name, tag)
                except RuntimeError as patch_err:
                    last_err = patch_err
            continue

    raise RuntimeError(
        f"Failed to ensure worktree for {repo_name}@{tag}: {last_err}"
    )


def build_github_url(
    org: str, repo_name: str, tag: str, rel_path: str, line_number: Optional[int] = None
) -> str:
    normalized_tag = tag if tag.startswith("v") else f"v{tag}"
    base = f"https://github.com/{org}/{repo_name}/blob/{normalized_tag}/{rel_path}"
    return f"{base}#L{line_number}" if line_number else base
