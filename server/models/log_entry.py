from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class LogFileMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_path: str        # original path or stored path
    stored_path: Optional[str] = None  # if copied into project
    file_type: str            # wso2carbon, audit, http_access, correlation, generic
    size_bytes: int
    line_count: Optional[int] = None
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None
    added: datetime = Field(default_factory=datetime.utcnow)
    is_reference: bool = False  # True if path reference, False if copied
    format_type_id: Optional[str] = None  # ID of the assigned LogFormatType


class LogEntry(BaseModel):
    line_number: int
    raw: str
    timestamp: Optional[str] = None       # "2025-12-16 04:47:44,782"
    timestamp_ms: Optional[int] = None    # epoch ms for sorting/ranging
    level: str = "INFO"                   # INFO, WARN, ERROR, DEBUG, TRACE, FATAL
    logger: str = ""                      # Full logger class name
    logger_short: str = ""                # Last segment after last dot
    message: str = ""
    thread: Optional[str] = None
    tenant_domain: Optional[str] = None
    tid: Optional[str] = None
    app_name: Optional[str] = None
    correlation_id: Optional[str] = None
    component: Optional[str] = None
    context_map: Optional[dict] = None
    stack_trace: Optional[list[str]] = None
    has_stack_trace: bool = False
    is_stack_trace_line: bool = False
    log_file_id: str = ""
