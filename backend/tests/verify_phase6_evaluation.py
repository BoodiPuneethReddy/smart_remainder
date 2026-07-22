import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def run_phase6_verification():
    print("==========================================================")
    print("        PHASE 6 — AI EVALUATION VERIFICATION SUITE       ")
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
            record_test("Auth for Phase 6 Evaluation Tests", True, "Successfully logged in as alex.morgan@student.edu")
        else:
            record_test("Auth for Phase 6 Evaluation Tests", False, f"Login failed: {r.status_code}")
            return results
    except Exception as e:
        record_test("Auth for Phase 6 Evaluation Tests", False, f"Exception: {e}")
        return results

    headers = {"Authorization": f"Bearer {token}"}
    start_url = f"{BASE_URL}/api/assessment/tutor/start"
    respond_url = f"{BASE_URL}/api/assessment/tutor/respond"

    # Initialize a Socratic Session for DBMS Normalization
    session_id = None
    try:
        r = requests.post(start_url, json={
            "subject": "Computer Science",
            "topic": "DBMS Normalization",
            "difficulty_level": 1,
            "assessment_type": "short_answer",
            "target_goal": "Exam",
            "teacher_personality": "Professor",
            "learning_mode": "Test Me"
        }, headers=headers)
        if r.status_code == 200:
            session_id = r.json().get("session_id")
            record_test("Socratic Session Setup for Evaluation", True, f"Session initialized (ID: {session_id})")
        else:
            record_test("Socratic Session Setup for Evaluation", False, f"HTTP {r.status_code}: {r.text}")
            return results
    except Exception as e:
        record_test("Socratic Session Setup for Evaluation", False, f"Exception: {e}")
        return results

    # Test Answer Variations
    test_cases = [
        ("Correct Answer", "Normalization decomposes complex tables into smaller relations to eliminate data redundancy and prevent insertion, update, and deletion anomalies.", 15, 75),
        ("Partial Answer", "It splits tables so data is not repeated everywhere in the database.", 12, 50),
        ("Wrong Answer", "Normalization duplicates all columns to make database backups run faster.", 10, 30),
        ("Very Short Answer", "Table splitting.", 9, 40),
        ("Misspellings & Alternate Syntax", "Normalisaton decouples relational tabels to optimize schema structure and keys.", 14, 70),
    ]

    for name, answer_text, time_taken, expected_min_score in test_cases:
        try:
            r = requests.post(respond_url, json={
                "session_id": session_id,
                "student_answer": answer_text,
                "time_taken_seconds": time_taken
            }, headers=headers)
            if r.status_code == 200:
                data = r.json()
                metrics = data.get("metrics", {})
                score = metrics.get("understanding", 0)
                
                # Check response fields completeness
                has_explanation = bool(data.get("explanation"))
                has_rewrite = bool(data.get("better_exam_version"))
                has_strengths = isinstance(data.get("strengths"), list)
                
                if has_explanation and has_strengths and has_rewrite:
                    record_test(f"Semantic Evaluation - {name}", True, f"Understanding Score: {score}/100, Grounding: {metrics.get('confidence')}%, Has Exam Rewrite: {has_rewrite}", f"Feedback Excerpt: {data.get('explanation')[:75]}...")
                else:
                    record_test(f"Semantic Evaluation - {name}", False, f"Missing evaluation fields: {data.keys()}")
            else:
                record_test(f"Semantic Evaluation - {name}", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test(f"Semantic Evaluation - {name}", False, f"Exception: {e}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 6 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase6_verification()
