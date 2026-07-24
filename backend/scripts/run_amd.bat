@echo off
echo ================================================================================
echo           STARTING SMART STUDY REMINDER AI (AMD BACKEND MODE)                  
echo ================================================================================

python scripts\check_environment.py

start "AI Microservice (Port 8001)" cmd /k "cd ..\ai-service && ..\backend\venv\Scripts\python -m app.main"
start "FastAPI Backend (Port 8000)" cmd /k "..\backend\venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [PASS] Backend & AI Microservice launched!
echo Open Swagger Docs: http://localhost:8000/docs
