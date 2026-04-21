from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["files"])


@router.get("/files/source")
async def read_source(
    path: str = Query(..., description="Absolute path to source file"),
    line: int | None = Query(None, description="Line number to center on"),
    context: int = Query(10, ge=0, le=200, description="Lines of context around `line`"),
):
    file_path = Path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))
    lines = text.splitlines()

    if line is None:
        return {
            "path": str(file_path),
            "totalLines": len(lines),
            "content": text,
        }

    start = max(0, line - 1 - context)
    end = min(len(lines), line + context)
    snippet = "\n".join(lines[start:end])
    return {
        "path": str(file_path),
        "totalLines": len(lines),
        "startLine": start + 1,
        "endLine": end,
        "targetLine": line,
        "content": snippet,
    }
