from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.models.log_format import LogFormatCreate, LogFormatUpdate
from server.core import format_manager
from server.core.pattern_compiler import test_pattern as _test_pattern

router = APIRouter(tags=["formats"])


@router.get("/formats")
async def list_formats():
    return {"formats": format_manager.list_formats()}


@router.post("/formats", status_code=201)
async def create_format(data: LogFormatCreate):
    try:
        fmt = format_manager.create_format(data)
        return fmt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/formats/{format_id}")
async def get_format(format_id: str):
    fmt = format_manager.get_format(format_id)
    if not fmt:
        raise HTTPException(status_code=404, detail="Format type not found")
    return fmt


@router.put("/formats/{format_id}")
async def update_format(format_id: str, updates: LogFormatUpdate):
    try:
        return format_manager.update_format(format_id, updates)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/formats/{format_id}")
async def delete_format(format_id: str):
    try:
        ok = format_manager.delete_format(format_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Format type not found")
        return {"deleted": True}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


class TestPatternRequest(BaseModel):
    pattern: str
    line: str


@router.post("/formats/test")
async def test_format_pattern(body: TestPatternRequest):
    return _test_pattern(body.pattern, body.line)
