import re
from typing import Optional
from server.models.repo import StackFrame, ResolvedFrame
from server.core import repo_registry, repo_resolver, repo_scanner


_FRAME_RE = re.compile(
    r"^\s*at\s+([\w$.]+)\.([\w$]+)\.([\w$<>]+)\(([\w$]+\.java):(\d+)\)\s*$"
)


WSO2_PACKAGE_PREFIXES = (
    "org.wso2",
    "org.apache.synapse",
    "org.apache.axis2",
    "org.apache.axiom",
    "org.apache.http.nio",
    "org.apache.http.impl.nio",
    "org.apache.commons.vfs2",
)


def _normalize(raw: str) -> str:
    return (
        raw.replace("\\n", "\n")
        .replace("\\r", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def parse_stack_trace(raw: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    for line in _normalize(raw).split("\n"):
        match = _FRAME_RE.match(line)
        if not match:
            continue
        package, class_name, method, file_name, line_str = match.groups()
        frames.append(
            StackFrame(
                packageName=package,
                className=class_name,
                methodName=method,
                fileName=file_name,
                lineNumber=int(line_str),
                raw=line.strip(),
            )
        )
    return frames


def is_wso2_frame(frame: StackFrame) -> bool:
    pkg = frame.packageName
    return any(pkg == p or pkg.startswith(p + ".") for p in WSO2_PACKAGE_PREFIXES)


def _read_snippet(file_path: str, line_number: int, context: int = 5) -> Optional[str]:
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return None
    start = max(0, line_number - 1 - context)
    end = min(len(lines), line_number + context)
    return "".join(lines[start:end])


def resolve_frame(frame: StackFrame) -> ResolvedFrame:
    """Resolve a single stack frame against all registered repos."""
    fqcn = f"{frame.packageName}.{frame.className}"
    base = ResolvedFrame(
        frame=frame.raw,
        resolved=False,
        packageName=frame.packageName,
        className=frame.className,
        methodName=frame.methodName,
        lineNumber=frame.lineNumber,
    )

    if not is_wso2_frame(frame):
        base.reason = "non_wso2_frame"
        return base

    repo_name, _ = repo_resolver.resolve_repo(frame.packageName)
    if repo_name is None:
        base.reason = "no_repo_mapping"
        return base

    repos = repo_registry.list_repos()
    for repo in repos:
        index = repo_registry.get_index(repo.id)
        if index is None:
            continue
        indexed = repo_scanner.lookup_class(index, fqcn)
        if indexed is None:
            continue
        snippet = _read_snippet(indexed.file_path, frame.lineNumber)
        return ResolvedFrame(
            frame=frame.raw,
            resolved=True,
            filePath=indexed.file_path,
            lineNumber=frame.lineNumber,
            repoLabel=repo.label,
            repoPath=repo.path,
            packageName=frame.packageName,
            className=frame.className,
            methodName=frame.methodName,
            snippet=snippet,
        )

    base.reason = "class_not_found_in_registered_repos"
    return base


def resolve_stack_trace(raw: str) -> list[ResolvedFrame]:
    frames = parse_stack_trace(raw)
    return [resolve_frame(f) for f in frames]
