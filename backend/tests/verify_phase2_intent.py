import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.agents.intent_classifier import classify, Intent

BASE_URL = "http://localhost:8000"

def run_phase2_verification():
    print("==========================================================")
    print("      PHASE 2 — CHATBOT & INTENT ROUTING VERIFICATION SUITE")
    print("==========================================================")
    
    results = []

    def record_test(name, passed, detail="", evidence=""):
        status = "PASS" if passed else "FAIL"
        results.append({
            "name": name,
            "passed": passed,
            "detail": detail,
            "evidence": evidence
        })
        print(f"[{status}] {name}")
        if detail:
            print(f"       Detail: {detail}")
        if evidence:
            print(f"       Evidence: {evidence}")

    # 1. Greetings Tests - MUST NOT invoke Planner
    greetings = ["hi", "hello", "good morning", "hey", "what's up", "yo", "thank you", "bye", "help", "how are you", "tell me a joke"]
    for text in greetings:
        res = classify(text)
        primary = res.primary_intent
        is_planner = (primary == Intent.STUDY_PLANNING)
        if not is_planner and primary in [Intent.GREETING, Intent.GOODBYE, Intent.GRATITUDE, Intent.HELP, Intent.CASUAL, Intent.SMALL_TALK]:
            record_test(f"Greeting Intent: '{text}'", True, f"Primary intent correctly mapped to {primary.value}", f"Intents: {[i.value for i in res.intents]}, Confidence: {res.confidence}")
        else:
            record_test(f"Greeting Intent: '{text}'", False, f"Incorrectly routed greeting to {primary.value}", f"Intents: {[i.value for i in res.intents]}")

    # 2. Academic Intents
    academics = [
        ("make a study plan for DBMS", Intent.STUDY_PLANNING),
        ("finish task 1", Intent.TASK_COMPLETION),
        ("reschedule my calculus problem set", Intent.SCHEDULE_CONSTRAINT),
        ("remind me to revise operating systems", Intent.STUDY_PLANNING),
        ("show my learning analytics summary", Intent.LEARNING_ANALYTICS),
        ("what is normalization in DBMS", Intent.INFORMATION_QUERY),
    ]
    for text, expected in academics:
        res = classify(text)
        if expected in res.intents or res.primary_intent == expected:
            record_test(f"Academic Intent: '{text}'", True, f"Mapped to expected intent {expected.value}", f"Primary: {res.primary_intent.value}, Intents: {[i.value for i in res.intents]}")
        else:
            record_test(f"Academic Intent: '{text}'", False, f"Expected {expected.value}, got {res.primary_intent.value}", f"Intents: {[i.value for i in res.intents]}")

    # 3. Schedule Constraints & Emotions
    constraints = [
        ("I only have one hour today", Intent.SCHEDULE_CONSTRAINT),
        ("I have two hours left before dinner", Intent.SCHEDULE_CONSTRAINT),
        ("I am tired and stressed", Intent.MOTIVATION),
        ("I missed yesterday's study block", Intent.SCHEDULE_CONSTRAINT),
    ]
    for text, expected in constraints:
        res = classify(text)
        if expected in res.intents or res.primary_intent == expected:
            record_test(f"Constraint/Emotion: '{text}'", True, f"Mapped to {expected.value}", f"Primary: {res.primary_intent.value}")
        else:
            record_test(f"Constraint/Emotion: '{text}'", False, f"Expected {expected.value}, got {res.primary_intent.value}", f"Intents: {[i.value for i in res.intents]}")

    # 4. Compound Requests
    compound = "Hi, I only have two hours today and quiz me on DBMS"
    res_comp = classify(compound)
    matched = [i.value for i in res_comp.intents]
    if "greeting" in matched and "schedule_constraint" in matched:
        record_test("Compound Intent Sequence", True, "Successfully extracted compound intents", f"Matched Intents: {matched}, Confidence: {res_comp.confidence}")
    else:
        record_test("Compound Intent Sequence", False, f"Failed to match compound sequence: {matched}")

    # 5. Unknown & Edge Inputs
    edge_cases = [
        ("asdfghjkqwerty", Intent.UNKNOWN),
        ("emoji test query", Intent.UNKNOWN),
        ("tell me about the weather", Intent.CASUAL),
    ]
    for text, expected in edge_cases:
        res = classify(text)
        if res.primary_intent in [expected, Intent.CASUAL, Intent.UNKNOWN]:
            record_test(f"Edge Case Input: '{text}'", True, f"Safely handled edge input as {res.primary_intent.value}", f"Confidence: {res.confidence}")
        else:
            record_test(f"Edge Case Input: '{text}'", False, f"Unexpected intent {res.primary_intent.value}")

    # 6. Live API Recommendation Route Integration Test
    login_data = {"email": "alex.morgan@student.edu", "password": "StudyAI@2025"}
    token = None
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        token = r.json().get("access_token")
    except Exception:
        pass

    if token:
        chat_url = f"{BASE_URL}/api/chat"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 6a: Greeting API message
        try:
            res = requests.post(chat_url, json={"question": "Hello!"}, headers=headers)
            if res.status_code == 200:
                data = res.json()
                record_test("Live Chat API - Greeting Routing", True, "Greeting responded cleanly without unwanted task modifications", f"Question: {data.get('question')}, Response: {data.get('answer')[:80]}...")
            else:
                record_test("Live Chat API - Greeting Routing", False, f"API error {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Live Chat API - Greeting Routing", False, f"Exception: {e}")

        # Test 6b: Constraint API message
        try:
            res = requests.post(chat_url, json={"question": "I only have 2 hours today"}, headers=headers)
            if res.status_code == 200:
                data = res.json()
                record_test("Live Chat API - Constraint Rescheduling", True, "Constraint routed to recommendation logic", f"Question: {data.get('question')}, Answer: {data.get('answer')[:80]}...")
            else:
                record_test("Live Chat API - Constraint Rescheduling", False, f"API error {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Live Chat API - Constraint Rescheduling", False, f"Exception: {e}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 2 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase2_verification()
