from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from server.config import FRONTEND_DIR
from server.api import projects, logs, parsing

app = FastAPI(title="WSO2 Log Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(parsing.router, prefix="/api")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Serve index.html for all non-API, non-static routes (SPA client-side routing)
    return FileResponse(str(FRONTEND_DIR / "index.html"))
