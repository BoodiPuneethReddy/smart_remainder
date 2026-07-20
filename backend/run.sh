#!/usr/bin/env bash
# run.sh — start the FastAPI backend
set -e

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null || true

# Verify .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env not found. Run ./setup.sh first."
    exit 1
fi

echo "==> Starting Smart Study Reminder AI Backend"
echo "==> AI_SERVICE_MODE: $(grep AI_SERVICE_MODE .env | cut -d= -f2)"
echo "==> API docs: http://localhost:8000/docs"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
