import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)


@dataclass
class IndexedClass:
    fqcn: str
    file_path: str  # absolute
    line_count: int


@dataclass
class RepoIndex:
    repo_path: str
    indexed_at: str
    file_count: int
    class_count: int
    classes: dict[str, IndexedClass] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "indexed_at": self.indexed_at,
            "file_count": self.file_count,
            "class_count": self.class_count,
            "classes": {k: asdict(v) for k, v in self.classes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepoIndex":
        return cls(
            repo_path=data["repo_path"],
            indexed_at=data["indexed_at"],
            file_count=data["file_count"],
            class_count=data["class_count"],
            classes={
                k: IndexedClass(**v) for k, v in data.get("classes", {}).items()
            },
        )


def _extract_package(java_file: Path) -> Optional[str]:
    try:
        text = java_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = _PACKAGE_RE.search(text)
    return match.group(1) if match else None


def _count_lines(java_file: Path) -> int:
    try:
        with open(java_file, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def build_index(repo_path: str | Path) -> RepoIndex:
    """Walk a repo and build {FQCN: IndexedClass} from every .java file."""
    repo_path = Path(repo_path).resolve()
    classes: dict[str, IndexedClass] = {}
    file_count = 0

    for java_file in repo_path.rglob("*.java"):
        # Skip common non-source dirs
        parts = set(java_file.parts)
        if parts & {"target", "build", ".git", "node_modules"}:
            continue
        file_count += 1
        pkg = _extract_package(java_file)
        class_name = java_file.stem
        fqcn = f"{pkg}.{class_name}" if pkg else class_name
        # First occurrence wins; tests rarely collide with main sources due to pkg naming
        if fqcn not in classes:
            classes[fqcn] = IndexedClass(
                fqcn=fqcn,
                file_path=str(java_file),
                line_count=_count_lines(java_file),
            )

    return RepoIndex(
        repo_path=str(repo_path),
        indexed_at=datetime.utcnow().isoformat(),
        file_count=file_count,
        class_count=len(classes),
        classes=classes,
    )


def save_index(index: RepoIndex, index_file: Path) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    with open(index_file, "w") as f:
        json.dump(index.to_dict(), f)


def load_index(index_file: Path) -> Optional[RepoIndex]:
    if not index_file.exists():
        return None
    try:
        with open(index_file) as f:
            return RepoIndex.from_dict(json.load(f))
    except (json.JSONDecodeError, KeyError):
        return None


def _normalize_class_name(class_name: str) -> str:
    """Strip inner-class, anonymous, and lambda suffixes for FQCN lookup."""
    # Lambda: Foo$$Lambda$123 -> Foo
    if "$$Lambda" in class_name:
        class_name = class_name.split("$$Lambda")[0]
    # Inner class or anonymous: Foo$Inner, Foo$1 -> Foo
    if "$" in class_name:
        class_name = class_name.split("$")[0]
    return class_name


def lookup_class(index: RepoIndex, fqcn: str) -> Optional[IndexedClass]:
    """Return IndexedClass for an FQCN, handling inner/anonymous/lambda forms."""
    if fqcn in index.classes:
        return index.classes[fqcn]

    # Normalize inner/anon/lambda suffixes
    if "." in fqcn:
        pkg, cls = fqcn.rsplit(".", 1)
        normalized = f"{pkg}.{_normalize_class_name(cls)}"
        if normalized in index.classes:
            return index.classes[normalized]
    return None
