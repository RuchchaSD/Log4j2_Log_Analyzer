from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from server.config import FRONTEND_DIR
from server.api import projects, logs, parsing, formats, repos, stacktrace, files


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that disables browser caching — keeps dev edits always fresh."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


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
app.include_router(formats.router, prefix="/api")
app.include_router(repos.router, prefix="/api")
app.include_router(stacktrace.router, prefix="/api")
app.include_router(files.router, prefix="/api")

app.mount("/static", NoCacheStaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Serve index.html for all non-API, non-static routes (SPA client-side routing)
    return FileResponse(
        str(FRONTEND_DIR / "index.html"),
        headers={"Cache-Control": "no-store"},
    )
