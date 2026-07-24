#!/usr/bin/env bash

echo "================================================================================"
echo "          STARTING SMART STUDY REMINDER AI (AMD BACKEND MODE)                  "
echo "================================================================================"

python3 scripts/check_environment.py

echo "Starting Standalone AI Service on port 8001..."
(cd ../ai-service && python3 -m app.main) &

echo "Starting FastAPI Backend on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
