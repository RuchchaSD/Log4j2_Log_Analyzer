import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from server.models.log_entry import LogFileMetadata
from server.core import project_manager
from server.config import ANALYZER_DIR_NAME
import aiofiles

router = APIRouter(tags=["logs"])

TIMESTAMP_RE = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


# ── Request body models ────────────────────────────────────────────────────────

class LogPathRequest(BaseModel):
    path: str


class LogFolderRequest(BaseModel):
    folder: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def detect_file_type(filename: str) -> str:
    name = filename.lower()
    if "wso2carbon" in name:
        return "wso2carbon"
    if "audit" in name:
        return "audit"
    if "http_access" in name or "access_log" in name:
        return "http_access"
    if "correlation" in name:
        return "correlation"
    return "generic"


def extract_metadata(file_path: Path) -> dict:
    """Extract line count and first/last timestamp from file."""
    try:
        size = file_path.stat().st_size
        first_ts = None
        last_ts = None
        line_count = 0
        first_lines: list[str] = []
        last_lines: list[str] = []

        with open(file_path, 'r', errors='replace') as f:
            for i, line in enumerate(f):
                line_count += 1
                if i < 10:
                    first_lines.append(line)
                last_lines.append(line)
                if len(last_lines) > 10:
                    last_lines.pop(0)

        for line in first_lines:
            m = TIMESTAMP_RE.search(line)
            if m:
                first_ts = m.group()
                break
        for line in reversed(last_lines):
            m = TIMESTAMP_RE.search(line)
            if m:
                last_ts = m.group()
                break

        return {
            "size_bytes": size,
            "line_count": line_count,
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
        }
    except Exception:
        return {
            "size_bytes": 0,
            "line_count": None,
            "first_timestamp": None,
            "last_timestamp": None,
        }


def _get_logs_file(project_id: str) -> Path:
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return Path(project.path) / ANALYZER_DIR_NAME / "logs.json"


def _load_logs(project_id: str) -> list[dict]:
    logs_file = _get_logs_file(project_id)
    if not logs_file.exists():
        return []
    with open(logs_file) as f:
        return json.load(f)


def _save_logs(project_id: str, logs: list[dict]):
    logs_file = _get_logs_file(project_id)
    with open(logs_file, 'w') as f:
        json.dump(logs, f, indent=2, default=str)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/logs/upload", status_code=201)
async def upload_log(
    project_id: str = Query(...),
    file: UploadFile = File(...),
    format_type_id: Optional[str] = Query(None),
):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Resolve format type: explicit > project default
    resolved_format = format_type_id or project.settings.defaultFormatTypeId

    dest_dir = Path(project.path) / "logs"
    dest_dir.mkdir(exist_ok=True)
    dest_path = dest_dir / file.filename

    async with aiofiles.open(dest_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    meta = extract_metadata(dest_path)
    log_file = LogFileMetadata(
        filename=file.filename,
        original_path=str(dest_path),
        stored_path=str(dest_path),
        file_type=detect_file_type(file.filename),
        is_reference=False,
        format_type_id=resolved_format,
        **meta,
    )
    logs = _load_logs(project_id)
    logs.append(json.loads(log_file.model_dump_json()))
    _save_logs(project_id, logs)
    return log_file


@router.post("/logs/path", status_code=201)
async def add_log_path(
    project_id: str = Query(...),
    format_type_id: Optional[str] = Query(None),
    body: LogPathRequest = None,
):
    if body is None or not body.path:
        raise HTTPException(status_code=400, detail="path required")

    file_path = Path(body.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {body.path}")

    project = project_manager.get_project(project_id)
    resolved_format = format_type_id or (project.settings.defaultFormatTypeId if project else None)

    meta = extract_metadata(file_path)
    log_file = LogFileMetadata(
        filename=file_path.name,
        original_path=str(file_path),
        file_type=detect_file_type(file_path.name),
        is_reference=True,
        format_type_id=resolved_format,
        **meta,
    )
    logs = _load_logs(project_id)
    logs.append(json.loads(log_file.model_dump_json()))
    _save_logs(project_id, logs)
    return log_file


@router.post("/logs/folder", status_code=201)
async def add_log_folder(
    project_id: str = Query(...),
    format_type_id: Optional[str] = Query(None),
    body: LogFolderRequest = None,
):
    if body is None or not body.folder:
        raise HTTPException(status_code=400, detail="folder required")

    folder_path = Path(body.folder)
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {body.folder}")

    project = project_manager.get_project(project_id)
    resolved_format = format_type_id or (project.settings.defaultFormatTypeId if project else None)

    added: list[LogFileMetadata] = []
    logs = _load_logs(project_id)
    existing_paths = {l["original_path"] for l in logs}

    for file_path in sorted(folder_path.rglob("*")):
        if file_path.suffix.lower() in (".log", ".txt") and file_path.is_file():
            if str(file_path) in existing_paths:
                continue
            meta = extract_metadata(file_path)
            log_file = LogFileMetadata(
                filename=file_path.name,
                original_path=str(file_path),
                file_type=detect_file_type(file_path.name),
                is_reference=True,
                format_type_id=resolved_format,
                **meta,
            )
            logs.append(json.loads(log_file.model_dump_json()))
            added.append(log_file)

    _save_logs(project_id, logs)
    return {"added": len(added), "files": added}


@router.get("/logs")
async def list_logs(project_id: str = Query(...)):
    logs = _load_logs(project_id)
    return {"logs": logs}


@router.delete("/logs/{log_id}")
async def delete_log(log_id: str, project_id: str = Query(...)):
    logs = _load_logs(project_id)
    new_logs = [l for l in logs if l["id"] != log_id]
    if len(new_logs) == len(logs):
        raise HTTPException(status_code=404, detail="Log file not found")
    _save_logs(project_id, new_logs)
    return {"deleted": True}


class LogFormatAssign(BaseModel):
    format_type_id: Optional[str] = None


@router.put("/logs/{log_id}/format")
async def set_log_format(log_id: str, project_id: str = Query(...), body: LogFormatAssign = LogFormatAssign()):
    """Assign (or clear) a format type on an already-registered log file."""
    logs = _load_logs(project_id)
    for l in logs:
        if l["id"] == log_id:
            l["format_type_id"] = body.format_type_id
            _save_logs(project_id, logs)
            # Invalidate cached index so next fetch re-parses with new format
            from server.core.log_indexer import invalidate_index
            invalidate_index(log_id)
            return l
    raise HTTPException(status_code=404, detail="Log file not found")
