# Smart Study Reminder AI — Standalone AI Service

The **AI Service** is an independent FastAPI microservice running on `http://localhost:8001`. It encapsulates all intelligent reasoning capabilities for the Smart Study Reminder system.

## 🚀 Microservice Architecture

```
FastAPI Backend (Port 8000)
    │
    ├── HTTP POST /planner         ──> AI Service (Port 8001) /planner
    ├── HTTP POST /recommendation  ──> AI Service (Port 8001) /recommendation
    ├── HTTP POST /tutor           ──> AI Service (Port 8001) /tutor
    └── HTTP POST /reminder        ──> AI Service (Port 8001) /reminder
```

## Endpoints

- `POST /planner` — Priority-based study schedule generation.
- `POST /recommendation` — Conversational query answering and intent classification.
- `POST /tutor` — Socratic tutor response evaluation, mode adaptation, and diagram triggers.
- `POST /reminder` — Dynamic urgency calculation and notification drafting.
- `GET /health` — Microservice health status.

## Execution

```bash
cd ai-service
pip install -r requirements.txt
python -m app.main
```
