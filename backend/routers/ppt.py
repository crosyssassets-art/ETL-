"""Router: PPT Upload & Instruction Extraction."""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.routers.projects import get_project
from backend.services.ppt_parser import parse_pptx
from backend.models.schemas import InstructionsResponse

router = APIRouter()


@router.post("/projects/{project_id}/upload-ppt")
async def upload_ppt(project_id: str, file: UploadFile = File(...)):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.lower().endswith((".ppt", ".pptx")):
        raise HTTPException(status_code=400, detail="Only .ppt/.pptx files accepted")

    ppt_path = os.path.join(project["project_dir"], "input.pptx")
    with open(ppt_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    instructions = parse_pptx(ppt_path)
    project["instructions"] = instructions
    project["ppt_path"] = ppt_path

    return {
        "project_id": project_id,
        "instructions": instructions,
        "total": len(instructions),
    }


@router.get("/projects/{project_id}/instructions")
def get_instructions(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "instructions": project.get("instructions", []),
        "total": len(project.get("instructions", [])),
    }
