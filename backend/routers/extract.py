"""Router: Compare & Extract — Match PPT instructions to Excel tables."""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import pandas as pd

from backend.routers.projects import get_project
from backend.services.matcher import match_instructions

router = APIRouter()


@router.post("/projects/{project_id}/extract-data")
def extract_data(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    instructions = project.get("instructions", [])
    excel_tables = project.get("excel_tables", [])

    if not instructions:
        raise HTTPException(status_code=400, detail="No PPT instructions found. Upload PPT first.")
    if not excel_tables:
        raise HTTPException(status_code=400, detail="No Excel tables found. Upload Excel first.")

    match_results = match_instructions(instructions, excel_tables)
    project["match_results"] = match_results

    # Save extracted data to Excel
    extracted_path = os.path.join(project["project_dir"], "extracted_data.xlsx")
    _save_extracted_excel(match_results, extracted_path)
    project["extracted_excel_path"] = extracted_path

    matched = [r for r in match_results if r["match_confidence"] != "unmatched"]
    unmatched = [r for r in match_results if r["match_confidence"] == "unmatched"]

    return {
        "status": "extracted",
        "total_instructions": len(match_results),
        "matches_found": len(matched),
        "unmatched": len(unmatched),
        "download_url": f"/api/v1/etl/projects/{project_id}/download-extracted-excel",
        "results": [
            {
                "id": r["id"],
                "slide_number": r["slide_number"],
                "raw_text": r["raw_text"],
                "type": r["type"],
                "matched_table": r.get("matched_table"),
                "matched_sheet": r.get("matched_sheet"),
                "match_confidence": r["match_confidence"],
                "match_score": r["match_score"],
                "matched_q_codes": r.get("matched_q_codes", []),
                "matched_column": r.get("matched_column"),
            }
            for r in match_results
        ],
    }


def _save_extracted_excel(match_results: list, out_path: str):
    """Write one sheet per matched table with its data."""
    seen_sheets = {}
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for r in match_results:
            if r.get("matched_table_data") is None:
                continue
            sheet_name = (r.get("matched_table") or "Sheet")[:31]
            # Avoid duplicate sheet names
            if sheet_name in seen_sheets:
                seen_sheets[sheet_name] += 1
                sheet_name = f"{sheet_name[:28]}_{seen_sheets[sheet_name]}"
            else:
                seen_sheets[sheet_name] = 0

            df = pd.DataFrame(r["matched_table_data"])
            df.to_excel(writer, sheet_name=sheet_name, index=False)


@router.get("/projects/{project_id}/download-extracted-excel")
def download_extracted_excel(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    path = project.get("extracted_excel_path")
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Extracted Excel not yet generated")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="extracted_data.xlsx",
    )
