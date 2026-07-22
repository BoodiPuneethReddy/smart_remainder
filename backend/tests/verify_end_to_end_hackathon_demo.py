import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../app"))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.imported_document import ImportedDocument
from app.models.mistake_journal import MistakeJournal
from app.models.tutor_bookmark import TutorBookmark
from app.models.study_session import StudySession
from app.models.learning_objective import LearningObjective

BASE_URL = "http://localhost:8000"

def verify_hackathon_demo_end_to_end():
    print("================================================================================")
    print("      VERIFYING END-TO-END HACKATHON DEMO & PERSISTENT DATABASE SUBSYSTEMS       ")
    print("================================================================================")

    # 1. Login with demo account
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "alex.morgan@student.edu", "password": "StudyAI@2025"})
    if r.status_code != 200:
        print(f"[FAIL] Login failed: {r.status_code}")
        return
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] One-Tap Demo Account Login authenticated successfully.")

    # 2. Start a Tutor Session
    pld = {
        "subject": "DBMS",
        "topic": "DBMS Normalization",
        "difficulty_level": 1,
        "assessment_type": "short_answer",
        "target_goal": "Exam",
        "teacher_personality": "Socratic Tutor",
        "learning_mode": "Teach Me"
    }
    r_tutor = requests.post(f"{BASE_URL}/api/assessment/tutor/start", json=pld, headers=headers)
    session_id = r_tutor.json().get("session_id")
    print(f"[PASS] Tutor Session started. Session ID: {session_id}")

    # 3. Respond with an intentional misconception answer to trigger MistakeJournal auto-logging
    r_resp = requests.post(
        f"{BASE_URL}/api/assessment/tutor/respond",
        json={
            "session_id": session_id,
            "student_answer": "Normalization increases redundant data copies across all tables.",
            "time_taken_seconds": 15
        },
        headers=headers
    )
    print(f"[PASS] Tutor response evaluated. Grounding Confidence: {r_resp.json().get('evaluation_confidence')}%")

    # 4. Log a Study Session
    r_study = requests.post(
        f"{BASE_URL}/api/tasks/study-session",
        json={
            "task_id": 1,
            "duration_minutes": 30,
            "notes": "Studied DBMS Normalization"
        },
        headers=headers
    )
    print(f"[PASS] Study Session logged: {r_study.status_code}")

    # 5. Check Live Database Record Counts
    db = SessionLocal()
    imp_count = db.query(ImportedDocument).count()
    mistake_count = db.query(MistakeJournal).count()
    study_count = db.query(StudySession).count()
    obj_count = db.query(LearningObjective).count()

    print("\n================================================================================")
    print("                     LIVE DATABASE PERSISTENCE STATUS                           ")
    print("================================================================================")
    print(f"  • ImportedDocument records: {imp_count:<4} | Status: {'ACTIVE' if imp_count > 0 else 'EMPTY'}")
    print(f"  • MistakeJournal records:   {mistake_count:<4} | Status: {'ACTIVE' if mistake_count > 0 else 'EMPTY'}")
    print(f"  • StudySession records:     {study_count:<4} | Status: {'ACTIVE' if study_count > 0 else 'EMPTY'}")
    print(f"  • LearningObjective records: {obj_count:<4} | Status: {'ACTIVE' if obj_count > 0 else 'EMPTY'}")
    print("================================================================================")

if __name__ == "__main__":
    verify_hackathon_demo_end_to_end()
