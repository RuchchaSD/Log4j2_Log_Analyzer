import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from server.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSettings
from server.config import ANALYZER_DIR_NAME, RECENTS_FILE, MAX_RECENT_PROJECTS


def create_project(data: ProjectCreate) -> Project:
    """Create a new project folder + project.json."""
    project_dir = Path(data.path) / data.name
    project_dir.mkdir(parents=True, exist_ok=True)
    analyzer_dir = project_dir / ANALYZER_DIR_NAME
    analyzer_dir.mkdir(exist_ok=True)
    (project_dir / "logs").mkdir(exist_ok=True)
    (project_dir / "reports").mkdir(exist_ok=True)
    (project_dir / "sessions").mkdir(exist_ok=True)

    project = Project(
        name=data.name,
        product=data.product,
        productVersion=data.productVersion,
        u2Level=data.u2Level,
        installPath=data.installPath,
        path=str(project_dir),
        settings=data.settings or ProjectSettings(),
    )
    _save_project(project)
    _add_to_recents(project)
    return project


def open_project(project_path: str) -> Project:
    """Open an existing project by path."""
    project_file = Path(project_path) / ANALYZER_DIR_NAME / "project.json"
    if not project_file.exists():
        raise FileNotFoundError(f"No project found at {project_path}")
    with open(project_file) as f:
        data = json.load(f)
    project = Project(**data)
    _add_to_recents(project)
    return project


def get_project(project_id: str) -> Optional[Project]:
    """Get project from recents by ID."""
    recents = list_recent_projects()
    for p in recents:
        if p.id == project_id:
            return open_project(p.path)
    return None


def update_project(project_id: str, updates: ProjectUpdate) -> Project:
    """Update project fields."""
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")
    update_data = updates.model_dump(exclude_none=True)
    update_data["updated"] = datetime.utcnow()
    for k, v in update_data.items():
        setattr(project, k, v)
    _save_project(project)
    return project


def delete_project(project_id: str) -> bool:
    """Delete project's .wso2analyzer folder and remove from recents."""
    project = get_project(project_id)
    if not project:
        return False
    analyzer_dir = Path(project.path) / ANALYZER_DIR_NAME
    if analyzer_dir.exists():
        shutil.rmtree(analyzer_dir)
    _remove_from_recents(project_id)
    return True


def list_recent_projects() -> list[Project]:
    """List recently opened projects."""
    if not RECENTS_FILE.exists():
        return []
    try:
        with open(RECENTS_FILE) as f:
            data = json.load(f)
        projects = []
        for p_data in data.get("recents", []):
            try:
                p = Project(**p_data)
                # verify it still exists
                if Path(p.path).exists():
                    projects.append(p)
            except Exception:
                pass
        return projects
    except Exception:
        return []


def _save_project(project: Project):
    project_file = Path(project.path) / ANALYZER_DIR_NAME / "project.json"
    project_file.parent.mkdir(parents=True, exist_ok=True)
    with open(project_file, "w") as f:
        json.dump(json.loads(project.model_dump_json()), f, indent=2, default=str)


def _add_to_recents(project: Project):
    RECENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    recents = list_recent_projects()
    # Remove existing entry with same id or path
    recents = [p for p in recents if p.id != project.id and p.path != project.path]
    recents.insert(0, project)
    recents = recents[:MAX_RECENT_PROJECTS]
    with open(RECENTS_FILE, "w") as f:
        json.dump(
            {"recents": [json.loads(p.model_dump_json()) for p in recents]},
            f, indent=2, default=str
        )


def _remove_from_recents(project_id: str):
    recents = list_recent_projects()
    recents = [p for p in recents if p.id != project_id]
    RECENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RECENTS_FILE, "w") as f:
        json.dump(
            {"recents": [json.loads(p.model_dump_json()) for p in recents]},
            f, indent=2, default=str
        )
