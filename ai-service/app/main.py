"""
ai-service/app/main.py — Standalone AI Service Entry Point (Port 8001)

Features:
  - Planner Engine (/planner)
  - Recommendation Engine (/recommendation)
  - Tutor Engine (/tutor)
  - Reminder Engine (/reminder)
  - Health Status (/health)
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import planner, recommendation, tutor, reminder

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("ai_service")

app = FastAPI(
    title="Smart Study Reminder AI — Standalone AI Service",
    description="Microservice exposing Planner, Recommendation, Tutor, and Reminder engines over HTTP.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(planner.router)
app.include_router(recommendation.router)
app.include_router(tutor.router)
app.include_router(reminder.router)


from pydantic import BaseModel
from typing import Dict, Any

class GenerateRequest(BaseModel):
    task: str
    context: Dict[str, Any]

@app.post("/generate")
def generate_task(req: GenerateRequest):
    task = req.task
    ctx = req.context
    subject = ctx.get("subject", "General Study")
    topic = ctx.get("topic", "Concepts")
    personality = ctx.get("teacher_personality", ctx.get("personality", "Socratic Tutor"))
    mode = ctx.get("learning_mode", "Teach Me")
    fmt = ctx.get("assessment_type", ctx.get("assessment_format", "Mixed"))
    goal = ctx.get("target_goal", ctx.get("goal", "General Learning"))

    if task == "tutor_init_prompt":
        res = f"[{personality} — {mode} Mode — {fmt} Format — Goal: {goal}] Welcome to your AI study session on **{topic}**! What is your primary objective today?"
    elif task == "tutor_evaluate_response":
        import json
        res = json.dumps({
            "understanding": 85,
            "reasoning": 80,
            "application": 75,
            "confidence": 88,
            "explanation": f"[{personality} Feedback] Excellent explanation for **{topic}**! You demonstrated high conceptual accuracy.",
            "misconceptions": [],
            "terminology": [topic],
            "strengths": ["Clear definition"],
            "missing_points": [],
            "better_exam_version": ctx.get("user_answer", ""),
            "should_draw_whiteboard": False,
            "diagram_data": None
        })
    else:
        res = f"AI Service response for task '{task}' ({topic})."

    return {"result": res, "text": res}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ai-service",
        "port": 8001,
        "engines": ["planner", "recommendation", "tutor", "reminder", "generate"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
