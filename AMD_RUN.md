# ⚡ Smart Study Reminder AI — AMD Execution Guide

This guide describes how judges and evaluators can run the Smart Study Reminder AI backend and standalone AI Service in environments without **Node.js** (such as AMD JupyterLab / bare-metal server environments).

---

## 🏛️ Architecture in AMD Mode

```
┌─────────────────────────────────────────────────────────┐
│                      AMD Environment                    │
│                                                         │
│  FastAPI Backend (Port 8000) ──HTTP──> AI Microservice  │
│          │                              (Port 8001)     │
│          ├── SQLite Database                            │
│          └── APScheduler Poller                         │
│                                                         │
│  Interactive Swagger UI: http://localhost:8000/docs     │
└─────────────────────────────────────────────────────────┘
```

> **Note**: In AMD Mode, Node.js and the React Frontend are intentionally skipped. Evaluators verify all end-to-end functionality via the interactive Swagger OpenAPI UI at `http://localhost:8000/docs`.

---

## 🚀 Quick Execution (2 Steps)

### Step 1: Health & Environment Check

Run the environment checker:

```bash
python backend/scripts/check_environment.py
```

Expected Output:
```
================================================================================
         SMART STUDY REMINDER AI — ENVIRONMENT HEALTH CHECK                      
================================================================================
[PASS] Python version: 3.10.x
[PASS] SQLite available
[PASS] FastAPI available
[PASS] Database connected
Node.js not installed.
Frontend intentionally skipped in AMD mode.
Backend + AI Service fully functional.

[PASS] Backend ready — Swagger API Docs serving at http://localhost:8000/docs
================================================================================
```

---

### Step 2: Launch Backend & AI Service

#### On Windows:
```cmd
backend\scripts\run_amd.bat
```

#### On Linux / macOS / AMD JupyterLab:
```bash
chmod +x backend/scripts/run_amd.sh
./backend/scripts/run_amd.sh
```

---

## 🧪 Evaluator Verification Tasks in Swagger UI (`http://localhost:8000/docs`)

1. **Login & Token Generation**:
   - `POST /api/auth/login` with `{"email": "punithgodof@gmail.com", "password": "Punith@123"}`.
   - Copy `access_token` into Swagger `Authorize` button.

2. **Verify Pre-Populated Demo Tasks**:
   - `GET /api/tasks` -> Returns 8 tasks with non-zero priority scores, estimated study hours, and AI explanations.

3. **Verify AI Study Planner**:
   - `POST /api/planner/generate` -> Returns priority-sorted schedule blocks.

4. **Verify Document Ingestion Pipeline**:
   - `POST /api/import/upload` -> Upload any PDF. Evaluates multi-pass reasoning, dates, and entities.

5. **Verify AI Service Microservice**:
   - `GET http://localhost:8001/health` -> Returns `{"status": "healthy", "service": "ai-service"}`.
