from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class Repo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    path: str
    branch: Optional[str] = None
    remoteUrl: Optional[str] = None
    created: datetime = Field(default_factory=datetime.utcnow)
    lastIndexed: Optional[datetime] = None
    fileCount: int = 0
    classCount: int = 0


class RepoCreate(BaseModel):
    label: str
    path: str
    branch: Optional[str] = None
    remoteUrl: Optional[str] = None


class StackFrame(BaseModel):
    packageName: str
    className: str
    methodName: str
    fileName: str
    lineNumber: int
    raw: str


class ResolvedFrame(BaseModel):
    frame: str
    resolved: bool
    reason: Optional[str] = None
    filePath: Optional[str] = None
    lineNumber: Optional[int] = None
    repoLabel: Optional[str] = None
    repoPath: Optional[str] = None
    packageName: Optional[str] = None
    className: Optional[str] = None
    methodName: Optional[str] = None
    snippet: Optional[str] = None
    githubUrl: Optional[str] = None


class StackTraceResolveRequest(BaseModel):
    stackTrace: str
    productDir: Optional[str] = None


class StackTraceResolveResponse(BaseModel):
    frames: list[ResolvedFrame]
    resolvedCount: int
    totalCount: int


class RepoResolveRequest(BaseModel):
    packageName: str


class RepoResolveResponse(BaseModel):
    packageName: str
    repo: Optional[str] = None
    matchedPrefix: Optional[str] = None


class EnsureWorktreeRequest(BaseModel):
    org: str
    repo: str
    version: str


class EnsureWorktreeResponse(BaseModel):
    org: str
    repo: str
    version: str
    worktreePath: str
    created: bool
