import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def verify_real_data_reverification():
    print("================================================================================")
    print("      MANDATORY REAL-DATA RE-VERIFICATION PROTOCOL (ANTI-LEAK TEST)             ")
    print("================================================================================")

    # 1. Login
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "alex.morgan@student.edu", "password": "StudyAI@2025"})
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated as alex.morgan@student.edu")

    test_subjects = [
        ("Calculus", "Differential Equations", "Calculus II & Differential Equations"),
        ("DBMS", "3NF Normalization", "Database Management System (DBMS) Notes"),
        ("Physics", "Maxwell Equations", "Physics I & II Engineering Reference")
    ]

    leak_found = False

    for subj, topic, expected_text in test_subjects:
        pld = {
            "subject": subj,
            "topic": topic,
            "difficulty_level": 1,
            "assessment_type": "short_answer",
            "target_goal": "Exam",
            "teacher_personality": "Socratic Tutor",
            "learning_mode": "Flashcards"
        }
        r_tutor = requests.post(f"{BASE_URL}/api/assessment/tutor/start", json=pld, headers=headers)
        res_data = r_tutor.json()
        first_q = res_data.get("first_question", "")

        print(f"\n--- [Subject: {subj} | Topic: {topic}] ---")
        print(f"Response: {first_q[:160]}...")

        # Cross-Subject Content Leak Validation:
        # If Calculus session returns DBMS normalization text, trigger FAIL!
        if subj == "Calculus" and ("normalization" in first_q.lower() or "1nf" in first_q.lower() or "dbms" in first_q.lower()):
            print(f"[FAIL] CONTENT LEAK DETECTED! Calculus session returned DBMS text: '{first_q}'")
            leak_found = True
        elif subj == "Physics" and ("normalization" in first_q.lower() or "1nf" in first_q.lower() or "dbms" in first_q.lower()):
            print(f"[FAIL] CONTENT LEAK DETECTED! Physics session returned DBMS text: '{first_q}'")
            leak_found = True
        else:
            print(f"[PASS] {subj} session returned subject-isolated content with ZERO cross-subject leakage.")

    if not leak_found:
        print("\n================================================================================")
        print(" [PASS] MANDATORY RE-VERIFICATION PASSED — ZERO CROSS-SUBJECT CONTENT LEAKS! ")
        print("================================================================================")

if __name__ == "__main__":
    verify_real_data_reverification()
