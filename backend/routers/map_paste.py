"""Router: Map & Paste — Render charts and write back into PPT."""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.routers.projects import get_project
from backend.services.chart_renderer import render_chart
from backend.services.ppt_writer import paste_charts_into_pptx

router = APIRouter()


@router.post("/projects/{project_id}/map-and-paste")
def map_and_paste(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    match_results = project.get("match_results", [])
    ppt_path = project.get("ppt_path")

    if not match_results:
        raise HTTPException(status_code=400, detail="No match results. Run extract-data first.")
    if not ppt_path or not os.path.isfile(ppt_path):
        raise HTTPException(status_code=400, detail="Original PPT not found.")

    charts_dir = os.path.join(project["project_dir"], "charts")
    os.makedirs(charts_dir, exist_ok=True)

    charts_inserted = 0
    symbols_handled = 0

    for result in match_results:
        try:
            chart_path = render_chart(result, charts_dir)
            result["chart_path"] = chart_path
            if result["type"] == "symbol":
                symbols_handled += 1
            else:
                charts_inserted += 1
        except Exception as e:
            result["chart_path"] = None
            result["chart_error"] = str(e)

    output_pptx_path = os.path.join(project["project_dir"], "output.pptx")
    paste_charts_into_pptx(ppt_path, match_results, output_pptx_path)
    project["output_pptx_path"] = output_pptx_path

    return {
        "status": "completed",
        "charts_inserted": charts_inserted,
        "symbols_handled": symbols_handled,
        "download_url": f"/api/v1/etl/projects/{project_id}/download-final-ppt",
    }


@router.get("/projects/{project_id}/download-final-ppt")
def download_final_ppt(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    path = project.get("output_pptx_path")
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Final PPT not yet generated")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="output_with_charts.pptx",
    )
