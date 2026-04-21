from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class LogFormatType(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    pattern: str            # log4j2 layout pattern string
    description: str = ""
    product: Optional[str] = None   # apim, is, mi, ei, generic
    is_builtin: bool = False
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class LogFormatCreate(BaseModel):
    name: str
    pattern: str
    description: str = ""
    product: Optional[str] = None


class LogFormatUpdate(BaseModel):
    name: Optional[str] = None
    pattern: Optional[str] = None
    description: Optional[str] = None
    product: Optional[str] = None
