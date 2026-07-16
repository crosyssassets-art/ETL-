"""
main.py — FastAPI application entry point.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import projects, ppt, excel, extract, map_paste

app = FastAPI(
    title="PPT-Excel ETL Automation API",
    description=(
        "Reads instructions from PowerPoint slides (text boxes, symbols, arrows), "
        "matches them to Excel tables, renders the correct chart type, "
        "and pastes results back into the exact PPT location."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ─────────────────────────────────────────────────────────────────
PREFIX = "/api/v1/etl"

app.include_router(projects.router, prefix=PREFIX, tags=["Projects"])
app.include_router(ppt.router,      prefix=PREFIX, tags=["PPT"])
app.include_router(excel.router,    prefix=PREFIX, tags=["Excel"])
app.include_router(extract.router,  prefix=PREFIX, tags=["Extract"])
app.include_router(map_paste.router, prefix=PREFIX, tags=["Map & Paste"])

# ── Serve frontend static files ────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# ── Ensure storage dir exists ──────────────────────────────────────────────────
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ETL Automation API"}
