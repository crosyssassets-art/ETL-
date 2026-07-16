#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ETL Studio — Start Script
# Run this from inside the "ETL automation and API" folder.
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ⚡ ETL Studio — PPT ↔ Excel Automation"
echo "  ────────────────────────────────────────"

# ── Check Python ─────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "  ❌ Python3 not found. Please install Python 3.9+."
  exit 1
fi

# ── Virtual environment ───────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "  📦 Creating virtual environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate

# ── Install dependencies ──────────────────────────────────────────
echo "  📦 Installing dependencies…"
pip install -q -r backend/requirements.txt

# ── Launch FastAPI ────────────────────────────────────────────────
echo ""
echo "  ✅ Starting server at http://localhost:8000"
echo "  📖 API docs at   http://localhost:8000/docs"
echo "  🖥  Frontend at   http://localhost:8000"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
