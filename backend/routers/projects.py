"""Router: Project initialization."""

import uuid
import os
from fastapi import APIRouter
from backend.models.schemas import ProjectCreateResponse

router = APIRouter()

# In-memory project store (keyed by project_id)
PROJECTS: dict = {}
STORAGE_ROOT = os.path.join(os.path.dirname(__file__), "..", "storage")


@router.post("/projects", response_model=ProjectCreateResponse)
def create_project():
    project_id = str(uuid.uuid4())
    project_dir = os.path.join(STORAGE_ROOT, project_id)
    os.makedirs(project_dir, exist_ok=True)
    PROJECTS[project_id] = {
        "project_id": project_id,
        "project_dir": project_dir,
        "instructions": [],
        "excel_tables": [],
        "match_results": [],
    }
    return {"project_id": project_id, "status": "created"}


def get_project(project_id: str) -> dict:
    return PROJECTS.get(project_id)
