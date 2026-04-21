from fastapi import APIRouter, HTTPException
from server.models.repo import (
    RepoCreate,
    RepoResolveRequest,
    RepoResolveResponse,
    EnsureWorktreeRequest,
    EnsureWorktreeResponse,
)
from server.core import repo_registry, repo_resolver, git_client

router = APIRouter(tags=["repos"])


@router.post("/repos", status_code=201)
async def create_repo(data: RepoCreate):
    try:
        return repo_registry.register_repo(data)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/repos")
async def list_repos():
    return {"repos": repo_registry.list_repos()}


@router.get("/repos/{repo_id}/status")
async def repo_status(repo_id: str):
    repo = repo_registry.get_repo(repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repo not found")
    index = repo_registry.get_index(repo_id)
    return {
        "repo": repo,
        "indexed": index is not None,
        "fileCount": repo.fileCount,
        "classCount": repo.classCount,
        "lastIndexed": repo.lastIndexed,
    }


@router.post("/repos/{repo_id}/reindex")
async def reindex_repo(repo_id: str):
    repo = repo_registry.reindex_repo(repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: str):
    if not repo_registry.delete_repo(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")
    return {"deleted": True}


@router.post("/repos/resolve", response_model=RepoResolveResponse)
async def resolve_repo(body: RepoResolveRequest):
    repo, matched = repo_resolver.resolve_repo(body.packageName)
    return RepoResolveResponse(
        packageName=body.packageName,
        repo=repo,
        matchedPrefix=matched,
    )


@router.post("/repos/ensure-worktree", response_model=EnsureWorktreeResponse)
async def ensure_worktree(body: EnsureWorktreeRequest):
    try:
        result = git_client.ensure_worktree(body.repo, body.version)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return EnsureWorktreeResponse(
        org=result.org,
        repo=result.repo_name,
        version=result.tag,
        worktreePath=result.local_path,
        created=result.created,
    )


@router.get("/features")
async def list_features():
    return {"features": repo_resolver.list_features()}
