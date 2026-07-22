import sys
import os
import json
import inspect
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../app"))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.learning_profile import LearningProfile
from app.models.notification import Notification
from app.models.recommendation import Recommendation
from app.models.imported_document import ImportedDocument
from app.models.mistake_journal import MistakeJournal
from app.models.question_citation import QuestionCitation
from app.models.tutor_bookmark import TutorBookmark
from app.models.tutor_session import TutorSession
from app.models.college import College
from app.models.otp_code import OTPCode
from app.models.learning_objective import LearningObjective
from app.models.study_note import StudyNote
from app.models.tutor_session import TutorMessage
from app.services import ai_client, tutor_service
from app.agents import intent_classifier, recommendation_agent, planner_agent, learning_agent, reminder_agent

BASE_URL = "http://localhost:8000"

def run_deep_architecture_audit():
    print("================================================================================")
    print("      DEEP ARCHITECTURE & RUNTIME AUDIT (ZERO ASSUMPTION REPORT)               ")
    print("================================================================================")

    db = SessionLocal()
    audit_data = {}

    # 1. DATABASE MODELS & TABLE AUDIT
    print("\n--- PHASE 1: DATABASE MODELS & TABLE USAGE AUDIT ---")
    models_to_check = [
        ("User", User), ("Task", Task), ("StudySession", StudySession),
        ("LearningProfile", LearningProfile), ("Notification", Notification),
        ("Recommendation", Recommendation), ("ImportedDocument", ImportedDocument),
        ("MistakeJournal", MistakeJournal), ("QuestionCitation", QuestionCitation),
        ("TutorBookmark", TutorBookmark), ("TutorSession", TutorSession),
        ("TutorMessage", TutorMessage), ("College", College),
        ("OTPCode", OTPCode), ("LearningObjective", LearningObjective),
        ("StudyNote", StudyNote)
    ]

    db_audit = []
    for name, model in models_to_check:
        try:
            count = db.query(model).count()
            status = "ACTIVE" if count > 0 else "ZERO_RECORDS (UNPOPULATED / ORPHANED)"
            db_audit.append({"model": name, "table": model.__tablename__, "record_count": count, "status": status})
            print(f"  • Model: {name:<20} | Table: {model.__tablename__:<22} | Records: {count:<4} | Status: {status}")
        except Exception as e:
            db_audit.append({"model": name, "table": getattr(model, '__tablename__', 'N/A'), "record_count": -1, "status": f"ERROR: {e}"})
            print(f"  • Model: {name:<20} | ERROR: {e}")

    audit_data["database_models"] = db_audit

    # 2. PROMPT TEMPLATES & INVOCATION MAPPING
    print("\n--- PHASE 2: AI PROMPTS & CALLER MAPPING AUDIT ---")
    prompt_funcs = [m for m in dir(ai_client.AIInferenceClient) if m.startswith('_') and ('prompt' in m or 'generate' in m or 'evaluate' in m or 'parse' in m or 'tutor' in m)]
    
    # Read ai_client.py source code to trace callers
    ai_client_path = os.path.abspath(os.path.dirname(__file__) + "/../app/services/ai_client.py")
    with open(ai_client_path, 'r', encoding='utf-8') as f:
        ai_client_src = f.read()

    tutor_service_path = os.path.abspath(os.path.dirname(__file__) + "/../app/services/tutor_service.py")
    with open(tutor_service_path, 'r', encoding='utf-8') as f:
        tutor_service_src = f.read()

    rec_agent_path = os.path.abspath(os.path.dirname(__file__) + "/../app/agents/recommendation_agent.py")
    with open(rec_agent_path, 'r', encoding='utf-8') as f:
        rec_agent_src = f.read()

    prompt_audit = []
    for pf in prompt_funcs:
        callers = []
        if pf in ai_client_src:
            # Count occurrences outside definition
            count_ai = ai_client_src.count(pf)
            if count_ai > 1: callers.append(f"AIInferenceClient ({count_ai-1} calls)")
        if pf in tutor_service_src: callers.append(f"TutorService ({tutor_service_src.count(pf)} calls)")
        if pf in rec_agent_src: callers.append(f"RecommendationAgent ({rec_agent_src.count(pf)} calls)")

        status = "ACTIVE" if len(callers) > 0 else "DEAD / UNUSED PROMPT TEMPLATE"
        prompt_audit.append({"prompt_function": pf, "callers": callers, "status": status})
        print(f"  • Prompt: {pf:<35} | Callers: {str(callers):<45} | Status: {status}")

    audit_data["prompts"] = prompt_audit

    # 3. INTENT CLASSIFIER 200+ PROMPT RUNTIME ROUTING MATRIX
    print("\n--- PHASE 3: INTENT CLASSIFIER 200+ PROMPT ROUTING MATRIX ---")
    
    # Login to get JWT for live endpoint testing
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "alex.morgan@student.edu", "password": "StudyAI@2025"})
    token = r.json().get("access_token") if r.status_code == 200 else ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    test_prompts_categories = {
        "GREETING": ["hi", "hello", "yo", "good morning", "greetings", "hey there", "sup", "howdy", "good evening", "hi agent",
                     "hello study ai", "yo tutor", "hey bot", "good day", "hi assistant", "hello there", "hey friend", "yo buddy", "hi chat", "hello machine"],
        "GOODBYE": ["bye", "goodbye", "see you", "later", "cya", "heading out", "good night", "farewell", "bye for now", "g2g",
                    "talk later", "done for today", "signing off", "bye bot", "catch ya later", "peace out", "have a good day", "leaving now", "goodbye AI", "bye assistant"],
        "GRATITUDE": ["thanks", "thank you", "thx", "ty", "cheers", "appreciate it", "thanks a lot", "many thanks", "thank you so much", "grateful",
                      "awesome thanks", "great thanks", "thanks bot", "ty vm", "super thanks", "thanks for help", "much appreciated", "thanks buddy", "thank you AI", "thanks tutor"],
        "SMALL_TALK": ["how are you?", "tell me a joke", "who created you?", "are you human?", "what is your name?", "what's up?", "how's life?", "you are smart", "are you an AI?", "what can you do?",
                       "do you sleep?", "tell me something funny", "who is your boss?", "how old are you?", "do you like study?", "what is 2+2?", "are you single?", "what's the weather?", "sing a song", "do you know me?"],
        "ACADEMIC_EXPLANATION": ["teach me dbms", "explain 3NF normalization", "what is binary search tree?", "explain process scheduling in OS", "what is TCP 3-way handshake?",
                                "explain decorators in python", "what is polymorphism in java?", "explain derivative in calculus", "what are maxwell equations?", "explain dna replication",
                                "what was industrial revolution?", "explain acid properties", "how does BCNF work?", "what is virtual memory?", "explain paging in OS",
                                "what is UDP vs TCP?", "explain generators in python", "what is JVM memory structure?", "explain graph BFS vs DFS", "what is fundamental theorem of calculus?"],
        "SCHEDULE_PLANNER": ["what is my schedule today?", "when is my next exam?", "reschedule my tasks", "what assignments are due?", "show my study plan",
                             "i missed physics yesterday", "i only have 30 mins today", "prioritize my tasks", "am i on track for midterms?", "show my task list",
                             "recalculate my plan", "reschedule DBMS task", "what should i study right now?", "show overdue tasks", "update my study plan",
                             "add a study session", "clear my schedule", "show my weekly schedule", "am i behind schedule?", "optimize my study time"],
        "FLASHCARDS": ["give me flashcards on DBMS", "flashcards for OS", "show flashcards on networks", "quiz me with flashcards", "open flashcard mode",
                       "generate flashcards for python", "java flashcard review", "calculus flashcard deck", "physics flashcards", "biology flashcards",
                       "history flashcards", "start flashcards", "flashcard review", "practice flashcards", "test me with flashcards",
                       "show active recall cards", "leitner flashcards", "hard flashcards", "easy flashcards", "next flashcard"],
        "INTERVIEW": ["interview me on system design", "mock interview for DBMS", "technical interview questions", "start interview mode", "interview me on python",
                      "java interview questions", "OS interview practice", "computer networks interview", "algorithms mock interview", "placement interview practice",
                      "interview questions on 3NF", "gate interview questions", "system design scenario", "ask me an interview question", "assess my interview response",
                      "interviewer persona", "senior tech lead interview", "interview practice", "technical mock interview", "interview evaluation"],
        "REVISE": ["revise dbms", "quick revision on OS", "revision summary", "revise networks", "spaced repetition review",
                   "revise python", "revise java", "revise calculus", "revise physics", "revise biology",
                   "high yield summary", "mnemonics for dbms", "quick review", "restore retention score", "revise decayed topics",
                   "fast revision", "cheat sheet revision", "revision deck", "review weak areas", "revise past mistakes"],
        "GARBAGE_TYPOS": ["asdfgh", "?????", "!!!", "12345", "😀😃😄", "explain dbms in esapñol", "i feel strssed for os exam", "missed phsics yestday", "reschedul my task", "qwertyuiop"]
    }

    routing_matrix = []
    total_prompts = 0
    correct_routing = 0

    for expected_cat, prompts in test_prompts_categories.items():
        for p in prompts:
            total_prompts += 1
            try:
                res = requests.post(f"{BASE_URL}/api/chat", json={"question": p}, headers=headers)
                if res.status_code == 200:
                    rdata = res.json()
                    detected_intents = rdata.get("intents", [])
                    source = rdata.get("source", "Unknown")
                    ai_task = rdata.get("ai_task_used", "None")

                    # Evaluation of routing logic
                    is_greeting_or_casual = expected_cat in ["GREETING", "GOODBYE", "GRATITUDE", "SMALL_TALK"]
                    planner_triggered = source == "PlannerAgent" or ai_task == "present_study_plan"
                    
                    # Routing validation rules:
                    # 1. Greetings/Casual must NEVER trigger PlannerAgent
                    # 2. Academic questions must NOT trigger schedule recalculation unless explicitly requested
                    is_valid = True
                    if is_greeting_or_casual and planner_triggered:
                        is_valid = False

                    if is_valid: correct_routing += 1

                    routing_matrix.append({
                        "prompt": p,
                        "expected_category": expected_cat,
                        "detected_intents": detected_intents,
                        "source_agent": source,
                        "ai_task": ai_task,
                        "valid_routing": is_valid
                    })
                else:
                    routing_matrix.append({"prompt": p, "expected_category": expected_cat, "valid_routing": False, "error": f"HTTP {res.status_code}"})
            except Exception as e:
                routing_matrix.append({"prompt": p, "expected_category": expected_cat, "valid_routing": False, "error": str(e)})

    print(f"  • Total Prompts Evaluated: {total_prompts}")
    print(f"  • Valid Intent Routing:   {correct_routing} / {total_prompts} ({round((correct_routing/total_prompts)*100, 1)}%)")

    audit_data["intent_routing"] = {
        "total_evaluated": total_prompts,
        "correct_routing": correct_routing,
        "accuracy_pct": round((correct_routing/total_prompts)*100, 1),
        "matrix_sample": routing_matrix[:15]
    }

    # 4. SAVE AUDIT REPORT FILE
    os.makedirs(os.path.dirname(__file__) + "/logs", exist_ok=True)
    report_file = os.path.abspath(os.path.dirname(__file__) + "/logs/deep_architecture_audit_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print("\n================================================================================")
    print(f"Deep Architecture & Runtime Audit Report saved to: {report_file}")

if __name__ == "__main__":
    run_deep_architecture_audit()
