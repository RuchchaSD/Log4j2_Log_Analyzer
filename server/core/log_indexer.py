"""In-memory index for parsed log entries. One index per log file."""
from __future__ import annotations
from collections import defaultdict
from server.models.log_entry import LogEntry
from server.core.log_parser import parse_log_file


class LogIndex:
    def __init__(self, log_file_id: str, file_path: str):
        self.log_file_id = log_file_id
        self.file_path = file_path
        self.entries: list[LogEntry] = []
        self._by_level: dict[str, list[int]] = defaultdict(list)   # level -> [line indices]
        self._by_component: dict[str, list[int]] = defaultdict(list)
        self._by_thread: dict[str, list[int]] = defaultdict(list)
        self._by_tenant: dict[str, list[int]] = defaultdict(list)
        self._by_correlation: dict[str, list[int]] = defaultdict(list)
        self.parsed = False

    def build(self):
        self.entries = parse_log_file(self.file_path, self.log_file_id)
        for i, e in enumerate(self.entries):
            self._by_level[e.level].append(i)
            if e.logger_short:
                self._by_component[e.logger_short].append(i)
            if e.logger:
                self._by_component[e.logger].append(i)
            if e.thread:
                self._by_thread[e.thread].append(i)
            if e.tenant_domain:
                self._by_tenant[e.tenant_domain].append(i)
            if e.correlation_id:
                self._by_correlation[e.correlation_id].append(i)
        self.parsed = True

    def get_entries(self, offset: int = 0, limit: int = 200) -> list[LogEntry]:
        return self.entries[offset:offset + limit]

    def filter_entries(
        self,
        levels: list[str] | None = None,
        components: list[str] | None = None,
        search: str | None = None,
        regex: bool = False,
        case_sensitive: bool = False,
        correlation_id: str | None = None,
        has_stack_trace: bool | None = None,
        time_from: str | None = None,
        time_to: str | None = None,
        offset: int = 0,
        limit: int = 500,
    ) -> tuple[list[LogEntry], int]:
        import re as _re

        # Start with all indices
        candidates = list(range(len(self.entries)))

        if levels:
            lvl_set = {l.upper() for l in levels}
            candidates = [i for i in candidates if self.entries[i].level in lvl_set]

        if components:
            comp_set = set(components)
            candidates = [i for i in candidates
                          if self.entries[i].logger_short in comp_set
                          or self.entries[i].logger in comp_set]

        if correlation_id:
            candidates = [i for i in candidates
                          if self.entries[i].correlation_id == correlation_id]

        if has_stack_trace is not None:
            candidates = [i for i in candidates
                          if self.entries[i].has_stack_trace == has_stack_trace]

        if time_from or time_to:
            candidates = [i for i in candidates
                          if self._in_time_range(self.entries[i], time_from, time_to)]

        if search:
            if regex:
                try:
                    flags = 0 if case_sensitive else _re.IGNORECASE
                    pat = _re.compile(search, flags)
                    candidates = [i for i in candidates
                                  if pat.search(self.entries[i].message)
                                  or pat.search(self.entries[i].raw)]
                except _re.error:
                    pass
            else:
                q = search if case_sensitive else search.lower()
                candidates = [i for i in candidates
                              if q in (self.entries[i].message if case_sensitive else self.entries[i].message.lower())
                              or q in (self.entries[i].raw if case_sensitive else self.entries[i].raw.lower())]

        total = len(candidates)
        page = [self.entries[i] for i in candidates[offset:offset + limit]]
        return page, total

    def get_summary(self) -> dict:
        level_counts: dict[str, int] = {}
        component_counts: dict[str, int] = {}
        for e in self.entries:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1
            if e.logger_short:
                component_counts[e.logger_short] = component_counts.get(e.logger_short, 0) + 1

        timestamps = [e.timestamp for e in self.entries if e.timestamp]
        return {
            "total_entries": len(self.entries),
            "level_counts": level_counts,
            "top_components": sorted(component_counts.items(), key=lambda x: -x[1])[:20],
            "first_timestamp": timestamps[0] if timestamps else None,
            "last_timestamp": timestamps[-1] if timestamps else None,
            "has_stack_traces": sum(1 for e in self.entries if e.has_stack_trace),
        }

    def get_groups(self, group_by: str) -> list[dict]:
        groups: dict[str, dict] = {}
        for e in self.entries:
            key = ""
            if group_by == "level":
                key = e.level
            elif group_by == "component":
                key = e.logger_short or e.logger or "unknown"
            elif group_by == "logger":
                key = e.logger or "unknown"
            elif group_by == "tenant":
                key = e.tenant_domain or "unknown"
            elif group_by == "correlationId":
                key = e.correlation_id or "unknown"
            else:
                key = e.level

            if key not in groups:
                groups[key] = {"key": key, "count": 0, "firstSeen": e.timestamp, "lastSeen": e.timestamp, "errorCount": 0}
            groups[key]["count"] += 1
            groups[key]["lastSeen"] = e.timestamp
            if e.level in ("ERROR", "FATAL"):
                groups[key]["errorCount"] += 1

        return sorted(groups.values(), key=lambda x: -x["count"])

    def _in_time_range(self, entry: LogEntry, time_from: str | None, time_to: str | None) -> bool:
        if not entry.timestamp:
            return True
        ts = entry.timestamp
        if time_from and ts < time_from:
            return False
        if time_to and ts > time_to:
            return False
        return True


# ── Global index registry (per-process) ───────────────────────────────────────
_indices: dict[str, LogIndex] = {}


def get_or_build_index(log_file_id: str, file_path: str) -> LogIndex:
    if log_file_id not in _indices or not _indices[log_file_id].parsed:
        idx = LogIndex(log_file_id, file_path)
        idx.build()
        _indices[log_file_id] = idx
    return _indices[log_file_id]


def invalidate_index(log_file_id: str):
    _indices.pop(log_file_id, None)
