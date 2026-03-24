from fastapi import APIRouter, HTTPException
from server.models.project import ProjectCreate, ProjectUpdate
from server.core import project_manager

router = APIRouter(tags=["projects"])


@router.post("/projects", status_code=201)
async def create_project(data: ProjectCreate):
    try:
        project = project_manager.create_project(data)
        return project
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects")
async def list_projects():
    projects = project_manager.list_recent_projects()
    return {"projects": projects}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}")
async def update_project(project_id: str, updates: ProjectUpdate):
    try:
        project = project_manager.update_project(project_id, updates)
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    ok = project_manager.delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


@router.post("/projects/open")
async def open_project(body: dict):
    path = body.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    try:
        project = project_manager.open_project(path)
        return project
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
