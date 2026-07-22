import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def run_phase5_verification():
    print("==========================================================")
    print("      PHASE 5 — AI TUTOR WORKSPACE VERIFICATION SUITE     ")
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

    # 1. Login
    login_data = {"email": "alex.morgan@student.edu", "password": "StudyAI@2025"}
    token = None
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if r.status_code == 200:
            token = r.json().get("access_token")
            record_test("Auth for Phase 5 Tutor Tests", True, "Successfully logged in as alex.morgan@student.edu")
        else:
            record_test("Auth for Phase 5 Tutor Tests", False, f"Login failed: {r.status_code}")
            return results
    except Exception as e:
        record_test("Auth for Phase 5 Tutor Tests", False, f"Exception: {e}")
        return results

    headers = {"Authorization": f"Bearer {token}"}
    start_url = f"{BASE_URL}/api/assessment/tutor/start"

    # 2. Test Different Personalities
    personalities = ["Professor", "Friendly Teacher", "Exam Coach", "Interviewer", "Socratic Tutor"]
    for p in personalities:
        start_data = {
            "subject": "Computer Science",
            "topic": "DBMS Normalization",
            "difficulty_level": 1,
            "assessment_type": "mixed",
            "target_goal": "General Learning",
            "teacher_personality": p,
            "learning_mode": "Teach Me"
        }
        try:
            r = requests.post(start_url, json=start_data, headers=headers)
            if r.status_code == 200:
                data = r.json()
                q = data.get("first_question", "")
                record_test(f"Personality Mode - '{p}'", True, f"Session initialized cleanly (Session ID: {data.get('session_id')})", f"Prompt Excerpt: {q[:75]}...")
            else:
                record_test(f"Personality Mode - '{p}'", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test(f"Personality Mode - '{p}'", False, f"Exception: {e}")

    # 3. Test Learning Modes
    learning_modes = ["Teach Me", "Test Me", "Revise", "Challenge Me", "Interview Me", "Flashcards", "Explain Mistakes", "Mixed"]
    for m in learning_modes:
        start_data = {
            "subject": "Mathematics",
            "topic": "Differential Calculus",
            "difficulty_level": 2,
            "assessment_type": "short_answer",
            "target_goal": "GATE",
            "teacher_personality": "Professor",
            "learning_mode": m
        }
        try:
            r = requests.post(start_url, json=start_data, headers=headers)
            if r.status_code == 200:
                data = r.json()
                q = data.get("first_question", "")
                record_test(f"Learning Mode - '{m}'", True, f"Configured {m} mode successfully", f"First Question: {q[:75]}...")
            else:
                record_test(f"Learning Mode - '{m}'", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test(f"Learning Mode - '{m}'", False, f"Exception: {e}")

    # 4. Test Assessment Formats
    formats = ["Multiple Choice", "Short Answer", "Long Answer", "Fill in the Blanks", "True / False", "Mixed"]
    for fmt in formats:
        start_data = {
            "subject": "Physics",
            "topic": "Quantum Mechanics",
            "difficulty_level": 3,
            "assessment_type": fmt.lower().replace(" ", "_"),
            "target_goal": "Mid Exam",
            "teacher_personality": "Socratic Tutor",
            "learning_mode": "Test Me"
        }
        try:
            r = requests.post(start_url, json=start_data, headers=headers)
            if r.status_code == 200:
                data = r.json()
                q = data.get("first_question", "")
                record_test(f"Assessment Format - '{fmt}'", True, f"Generated format {fmt}", f"Question: {q[:75]}...")
            else:
                record_test(f"Assessment Format - '{fmt}'", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test(f"Assessment Format - '{fmt}'", False, f"Exception: {e}")

    # 5. Test Study Goals
    goals = ["College", "Semester", "Mid Exam", "Placement", "Interview", "GATE", "General Learning"]
    for g in goals:
        start_data = {
            "subject": "Data Structures",
            "topic": "Binary Search Trees",
            "difficulty_level": 1,
            "assessment_type": "mixed",
            "target_goal": g,
            "teacher_personality": "Interviewer",
            "learning_mode": "Interview Me"
        }
        try:
            r = requests.post(start_url, json=start_data, headers=headers)
            if r.status_code == 200:
                data = r.json()
                record_test(f"Study Goal - '{g}'", True, f"Goal {g} configured cleanly", f"Session ID: {data.get('session_id')}")
            else:
                record_test(f"Study Goal - '{g}'", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test(f"Study Goal - '{g}'", False, f"Exception: {e}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 5 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase5_verification()
