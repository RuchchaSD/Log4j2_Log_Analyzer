import re
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from server.core import log_indexer
from server.core.project_manager import get_project
from server.api.logs import _load_logs
from server.config import ANALYZER_DIR_NAME
from pathlib import Path

router = APIRouter(tags=["parsing"])


def _resolve_log_file(project_id: str, log_id: str) -> tuple[str, str, str | None]:
    """Returns (log_file_id, file_path, format_type_id). Raises 404 if not found."""
    logs = _load_logs(project_id)
    for l in logs:
        if l["id"] == log_id:
            path = l.get("stored_path") or l.get("original_path")
            if not path or not Path(path).exists():
                raise HTTPException(status_code=404, detail="Log file not accessible on disk")
            return l["id"], path, l.get("format_type_id")
    raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/logs/{log_id}/entries")
async def get_log_entries(
    log_id: str,
    project_id: str = Query(...),
    offset: int = 0,
    limit: int = 200,
):
    fid, path, fmt_id = _resolve_log_file(project_id, log_id)
    idx = log_indexer.get_or_build_index(fid, path, format_type_id=fmt_id)
    entries = idx.get_entries(offset, limit)
    return {
        "entries": entries,
        "total": len(idx.entries),
        "offset": offset,
        "limit": limit,
    }


@router.get("/logs/{log_id}/summary")
async def get_log_summary(log_id: str, project_id: str = Query(...)):
    fid, path, fmt_id = _resolve_log_file(project_id, log_id)
    idx = log_indexer.get_or_build_index(fid, path, format_type_id=fmt_id)
    return idx.get_summary()


class FilterRequest(BaseModel):
    levels: Optional[list[str]] = None
    components: Optional[list[str]] = None
    search: Optional[str] = None
    regex: bool = False
    case_sensitive: bool = False
    correlation_id: Optional[str] = None
    has_stack_trace: Optional[bool] = None
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    offset: int = 0
    limit: int = 500


@router.post("/logs/{log_id}/filter")
async def filter_log_entries(log_id: str, project_id: str = Query(...), body: FilterRequest = FilterRequest()):
    fid, path, fmt_id = _resolve_log_file(project_id, log_id)
    idx = log_indexer.get_or_build_index(fid, path, format_type_id=fmt_id)
    entries, total = idx.filter_entries(
        levels=body.levels,
        components=body.components,
        search=body.search,
        regex=body.regex,
        case_sensitive=body.case_sensitive,
        correlation_id=body.correlation_id,
        has_stack_trace=body.has_stack_trace,
        time_from=body.time_from,
        time_to=body.time_to,
        offset=body.offset,
        limit=body.limit,
    )
    return {"entries": entries, "total": total, "offset": body.offset, "limit": body.limit}


@router.get("/logs/{log_id}/groups/{group_by}")
async def get_log_groups(log_id: str, group_by: str, project_id: str = Query(...)):
    valid = {"level", "component", "logger", "tenant", "correlationId"}
    if group_by not in valid:
        raise HTTPException(status_code=400, detail=f"group_by must be one of {valid}")
    fid, path, fmt_id = _resolve_log_file(project_id, log_id)
    idx = log_indexer.get_or_build_index(fid, path, format_type_id=fmt_id)
    return {"groups": idx.get_groups(group_by)}


class SearchRequest(BaseModel):
    query: str
    regex: bool = False
    case_sensitive: bool = False
    log_file_ids: Optional[list[str]] = None  # None means all
    levels: Optional[list[str]] = None
    limit: int = 100


@router.post("/logs/search")
async def search_logs(project_id: str = Query(...), body: SearchRequest = ...):
    logs_meta = _load_logs(project_id)

    if body.log_file_ids:
        logs_meta = [l for l in logs_meta if l["id"] in body.log_file_ids]

    all_results = []
    for l in logs_meta:
        path = l.get("stored_path") or l.get("original_path")
        if not path or not Path(path).exists():
            continue
        idx = log_indexer.get_or_build_index(l["id"], path, format_type_id=l.get("format_type_id"))
        entries, _ = idx.filter_entries(
            levels=body.levels,
            search=body.query,
            regex=body.regex,
            case_sensitive=body.case_sensitive,
            limit=body.limit,
        )
        all_results.extend(entries)
        if len(all_results) >= body.limit:
            break

    return {"results": all_results[:body.limit], "total": len(all_results)}
