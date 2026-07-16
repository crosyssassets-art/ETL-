"""Router: Excel Upload & Table Normalisation."""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.routers.projects import get_project
from backend.services.excel_parser import parse_excel

router = APIRouter()


@router.post("/projects/{project_id}/upload-excel")
async def upload_excel(project_id: str, file: UploadFile = File(...)):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only .xls/.xlsx files accepted")

    excel_path = os.path.join(project["project_dir"], "input.xlsx")
    with open(excel_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    tables = parse_excel(excel_path)
    project["excel_tables"] = tables
    project["excel_path"] = excel_path

    # Return lightweight response (no dataframes)
    normalized_names = [t["normalized_name"] for t in tables]
    return {
        "status": "success",
        "tables_detected": len(tables),
        "normalized_names": normalized_names,
        "table_details": [
            {
                "sheet_name": t["sheet_name"],
                "table_name": t["table_name"],
                "normalized_name": t["normalized_name"],
                "question_codes": t["question_codes"],
                "row_count": t["row_count"],
                "col_count": t["col_count"],
            }
            for t in tables
        ],
    }
