import re
from datetime import datetime
from typing import Optional
from server.models.log_entry import LogEntry


# Timestamp parsing: "2025-12-16 04:47:44,782" -> epoch ms
def _parse_ts_ms(ts_str: str) -> Optional[int]:
    try:
        dt = datetime.strptime(ts_str.replace(',', '.'), "%Y-%m-%d %H:%M:%S.%f")
        return int(dt.timestamp() * 1000)
    except:
        return None


def _short_logger(logger: str) -> str:
    return logger.split('.')[-1] if '.' in logger else logger


STACK_LINE_RE = re.compile(r'^\s+at |^Caused by:|^\s+\.\.\.|^java\.|^\s+Suppressed:')

TID_RE = re.compile(
    r'^TID:\s*\[([^\]]*)\]\s*\[([^\]]*)\]\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\]\s+(\w+)\s+\{([^}]+)\}\s+-\s+(.*)',
    re.DOTALL
)
BRACKET_RE = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\]\s+(\w+)\s+-\s+(\S+)\s+(.*)',
    re.DOTALL
)
BASIC_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+(\w+)\s+\[([^\]]+)\]\s+-\s+(.*)',
    re.DOTALL
)


def detect_format(first_lines: list[str]) -> str:
    """Detect log format from first non-empty lines."""
    for line in first_lines:
        if TID_RE.match(line):
            return "tid"
        if BRACKET_RE.match(line):
            return "bracket"
        if BASIC_RE.match(line):
            return "basic"
    return "tid"  # default


def parse_log_file(file_path: str, log_file_id: str) -> list[LogEntry]:
    """Parse a log file into a list of LogEntry objects with stack traces attached."""
    with open(file_path, 'r', errors='replace') as f:
        raw_lines = f.readlines()

    # Detect format
    first_lines = [l for l in raw_lines[:30] if l.strip()]
    fmt = detect_format(first_lines)

    entries: list[LogEntry] = []
    current_entry: Optional[LogEntry] = None

    for i, raw in enumerate(raw_lines):
        line = raw.rstrip('\n')
        line_num = i + 1

        # Try to parse as a new log entry
        entry = _try_parse_line(line, line_num, fmt, log_file_id)

        if entry:
            if current_entry:
                entries.append(current_entry)
            current_entry = entry
        elif current_entry and STACK_LINE_RE.match(line):
            # Stack trace line — attach to current entry
            if current_entry.stack_trace is None:
                current_entry.stack_trace = []
                current_entry.has_stack_trace = True
            current_entry.stack_trace.append(line)
        elif current_entry and line.strip():
            # Continuation line — append to message
            current_entry.message += '\n' + line
        # blank lines between entries: skip

    if current_entry:
        entries.append(current_entry)

    return entries


def _try_parse_line(line: str, line_num: int, fmt: str, log_file_id: str) -> Optional[LogEntry]:
    """Try to parse a line as a new log entry. Returns None if not a log header."""
    m = TID_RE.match(line)
    if m:
        tid, app_name, ts, level, logger, message = m.groups()
        ts = ts.strip()
        return LogEntry(
            line_number=line_num,
            raw=line,
            timestamp=ts,
            timestamp_ms=_parse_ts_ms(ts),
            level=level.strip().upper(),
            logger=logger.strip(),
            logger_short=_short_logger(logger.strip()),
            message=message.strip(),
            tid=tid.strip() or None,
            app_name=app_name.strip() or None,
            log_file_id=log_file_id,
        )

    m = BRACKET_RE.match(line)
    if m:
        ts, level, logger, message = m.groups()
        ts = ts.strip()
        return LogEntry(
            line_number=line_num,
            raw=line,
            timestamp=ts,
            timestamp_ms=_parse_ts_ms(ts),
            level=level.strip().upper(),
            logger=logger.strip(),
            logger_short=_short_logger(logger.strip()),
            message=message.strip(),
            log_file_id=log_file_id,
        )

    m = BASIC_RE.match(line)
    if m:
        ts, level, logger, message = m.groups()
        ts = ts.strip()
        return LogEntry(
            line_number=line_num,
            raw=line,
            timestamp=ts,
            timestamp_ms=_parse_ts_ms(ts),
            level=level.strip().upper(),
            logger=logger.strip(),
            logger_short=_short_logger(logger.strip()),
            message=message.strip(),
            log_file_id=log_file_id,
        )

    return None
