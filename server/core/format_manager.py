"""CRUD operations for log format types.

Built-in formats are always present (read-only).
User-defined formats are persisted to ~/.wso2analyzer/log_formats.json.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from server.models.log_format import LogFormatType, LogFormatCreate, LogFormatUpdate
from server.config import LOG_FORMATS_FILE


# ── Built-in formats ──────────────────────────────────────────────────────────

_BUILTINS: list[LogFormatType] = [
    LogFormatType(
        id="builtin-tid",
        name="APIM / IS Carbon (TID format)",
        pattern="TID: [%tenantId] [%appName] [%d] %5p {%c} - %m%ex%n",
        description="WSO2 API Manager and Identity Server — Carbon log in TID format (most common)",
        product="apim",
        is_builtin=True,
    ),
    LogFormatType(
        id="builtin-bracket",
        name="MI / EI Carbon (bracket format)",
        pattern="[%d] %5p {%c} - %m%ex%n",
        description="WSO2 Micro Integrator and Enterprise Integrator — Carbon log in bracket format",
        product="mi",
        is_builtin=True,
    ),
    LogFormatType(
        id="builtin-basic",
        name="Basic Carbon (generic fallback)",
        pattern="%d %5p [%c] - %m%ex%n",
        description="Basic Carbon log format — used as auto-detection fallback",
        product="generic",
        is_builtin=True,
    ),
]

_BUILTIN_MAP: dict[str, LogFormatType] = {f.id: f for f in _BUILTINS}


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_user_formats() -> list[LogFormatType]:
    if not LOG_FORMATS_FILE.exists():
        return []
    try:
        with open(LOG_FORMATS_FILE) as f:
            data = json.load(f)
        return [LogFormatType(**item) for item in data.get("formats", [])]
    except Exception:
        return []


def _save_user_formats(formats: list[LogFormatType]):
    LOG_FORMATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FORMATS_FILE, "w") as f:
        json.dump(
            {"formats": [json.loads(fmt.model_dump_json()) for fmt in formats]},
            f, indent=2, default=str,
        )


# ── Public API ────────────────────────────────────────────────────────────────

def list_formats() -> list[LogFormatType]:
    """Return all formats: built-ins first, then user-defined."""
    return list(_BUILTINS) + _load_user_formats()


def get_format(format_id: str) -> Optional[LogFormatType]:
    if format_id in _BUILTIN_MAP:
        return _BUILTIN_MAP[format_id]
    for fmt in _load_user_formats():
        if fmt.id == format_id:
            return fmt
    return None


def create_format(data: LogFormatCreate) -> LogFormatType:
    """Create a new user-defined format. Raises ValueError on duplicate name."""
    existing = list_formats()
    if any(f.name.lower() == data.name.lower() for f in existing):
        raise ValueError(f"A format type named '{data.name}' already exists")
    fmt = LogFormatType(
        name=data.name,
        pattern=data.pattern,
        description=data.description,
        product=data.product,
        is_builtin=False,
    )
    user_formats = _load_user_formats()
    user_formats.append(fmt)
    _save_user_formats(user_formats)
    return fmt


def update_format(format_id: str, updates: LogFormatUpdate) -> LogFormatType:
    """Update a user-defined format. Raises ValueError if not found or builtin."""
    if format_id in _BUILTIN_MAP:
        raise PermissionError(f"Cannot modify built-in format '{format_id}'")
    user_formats = _load_user_formats()
    for i, fmt in enumerate(user_formats):
        if fmt.id == format_id:
            update_data = updates.model_dump(exclude_none=True)
            update_data["updated"] = datetime.utcnow()
            for k, v in update_data.items():
                setattr(fmt, k, v)
            user_formats[i] = fmt
            _save_user_formats(user_formats)
            return fmt
    raise ValueError(f"Format '{format_id}' not found")


def delete_format(format_id: str) -> bool:
    """Delete a user-defined format. Raises PermissionError if builtin."""
    if format_id in _BUILTIN_MAP:
        raise PermissionError(f"Cannot delete built-in format '{format_id}'")
    user_formats = _load_user_formats()
    new_formats = [f for f in user_formats if f.id != format_id]
    if len(new_formats) == len(user_formats):
        return False
    _save_user_formats(new_formats)
    return True
