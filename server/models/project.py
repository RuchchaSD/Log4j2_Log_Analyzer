from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class ProjectSettings(BaseModel):
    largeLogMode: bool = False
    largeLogThresholdMB: int = 100
    slowOperationThresholdMs: int = 5000
    timezone: str = "UTC"
    defaultFormatTypeId: Optional[str] = None  # default LogFormatType for new log files


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    name: str
    product: str  # apim, is, mi, ei
    productVersion: str
    u2Level: Optional[str] = None
    installPath: Optional[str] = None
    path: str  # project folder path on disk
    repos: list[str] = []
    logFiles: list[str] = []
    notes: str = ""
    tags: list[str] = []
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectCreate(BaseModel):
    name: str
    product: str
    productVersion: str
    path: str  # where to create the project folder
    u2Level: Optional[str] = None
    installPath: Optional[str] = None
    settings: Optional[ProjectSettings] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    product: Optional[str] = None
    productVersion: Optional[str] = None
    u2Level: Optional[str] = None
    installPath: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    settings: Optional[ProjectSettings] = None
