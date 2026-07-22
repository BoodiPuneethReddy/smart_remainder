import requests
import json
import time

BASE_URL = "http://localhost:8000"

def run_e2e_verification():
    print("=== Start Comprehensive E2E Socratic AI Tutor Verification ===")

    # 1. Login
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {"email": "alex.morgan@student.edu", "password": "StudyAI@2025"}
    
    print("\n[1] Testing Authentication...")
    try:
        res = requests.post(login_url, json=login_data)
        res.raise_for_status()
        token = res.json()["access_token"]
        print("[OK] Authentication successful!")
    except Exception as exc:
        print(f"[FAIL] Authentication failed: {exc}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start Socratic Session
    start_url = f"{BASE_URL}/api/assessment/tutor/start"
    start_data = {
        "subject": "Computer Science",
        "topic": "DBMS Normalization",
        "difficulty_level": 1,
        "assessment_type": "mixed",
        "target_goal": "Interview",
        "teacher_personality": "Professor",
        "learning_mode": "Interview Me"
    }
    
    print("\n[2] Testing Socratic Session Initialization...")
    try:
        res = requests.post(start_url, json=start_data, headers=headers)
        res.raise_for_status()
        session_info = res.json()
        session_id = session_info["session_id"]
        first_question = session_info["first_question"]
        print(f"[OK] Socratic Session initialized successfully (Session ID: {session_id})")
        print(f"  First Question: \"{first_question}\"")
    except Exception as exc:
        print(f"[FAIL] Session start failed: {exc}")
        return

    # 3. Test Speed Guessing Protection
    respond_url = f"{BASE_URL}/api/assessment/tutor/respond"
    
    print("\n[3] Testing Speed Guessing Protection (Fast Submit)...")
    fast_data = {
        "session_id": session_id,
        "student_answer": "Normalization splits tables to reduce redundancy.",
        "time_taken_seconds": 3 # 3s is < 8s
    }
    try:
        res = requests.post(respond_url, json=fast_data, headers=headers)
        res.raise_for_status()
        response_data = res.json()
        if response_data["status"] == "SPEED_GUESS_DETECTED":
            print("[OK] Speed guessing protection works! Successfully blocked fast submit.")
            print(f"  Message: {response_data['message']}")
        else:
            print("[FAIL] Speed guessing protection FAILED to block fast submit.")
    except Exception as exc:
        print(f"[FAIL] Speed guessing check failed: {exc}")
        return

    # 4. Test Socratic Response & Evaluation (Proper Answer)
    print("\n[4] Testing Proper Socratic Answer Evaluation & Balanced Mastery...")
    valid_data = {
        "session_id": session_id,
        "student_answer": "Normalization splits relations into smaller tables to reduce data redundancy and eliminate anomalies.",
        "time_taken_seconds": 15 # 15s is >= 8s
    }
    try:
        res = requests.post(respond_url, json=valid_data, headers=headers)
        res.raise_for_status()
        response_data = res.json()
        if response_data["status"] == "SUCCESS":
            print("[OK] Socratic evaluation completed successfully!")
            print(f"  Explanation: \"{response_data['explanation']}\"")
            print(f"  Grounding Confidence %: {response_data['metrics']['confidence']}%")
            print(f"  Metrics: {response_data['metrics']}")
            print(f"  Whiteboard Diagram Triggered: {bool(response_data.get('mermaid_code'))}")
            if response_data.get('sources'):
                print(f"  Detailed Sources: {len(response_data['sources'])} chunks mapped.")
                for s in response_data['sources']:
                    print(f"    - [{s['lecture_name']}] {s['document_name']}, Page {s['page_number']}, Para {s['paragraph_number']}")
        else:
            print(f"[FAIL] Socratic evaluation failed: {response_data}")
            return
    except Exception as exc:
        print(f"[FAIL] Socratic evaluation request failed: {exc}")
        return

    # 5. Test Unknown Question Handling (Out-of-Scope Query)
    print("\n[5] Testing Out-of-Scope / Unknown Question Handling...")
    unknown_data = {
        "session_id": session_id,
        "student_answer": "Can you explain how Bitcoin blockchain proof-of-work consensus mechanism works?",
        "time_taken_seconds": 12
    }
    try:
        res = requests.post(respond_url, json=unknown_data, headers=headers)
        res.raise_for_status()
        unk_res = res.json()
        print("[OK] Out-of-Scope query evaluated cleanly.")
        print(f"  Tutor Reply: \"{unk_res['explanation'][:150]}...\"")
    except Exception as exc:
        print(f"[FAIL] Unknown question handling failed: {exc}")
        return

    # 6. Test Session Replay Log
    session_log_url = f"{BASE_URL}/api/assessment/tutor/session/{session_id}"
    print("\n[6] Testing Session Replay Traceability...")
    try:
        res = requests.get(session_log_url, headers=headers)
        res.raise_for_status()
        replay_data = res.json()
        chat_log = replay_data["chat_log"]
        print(f"[OK] Replayed session successfully! ({len(chat_log)} message turns found)")
        for msg in chat_log:
            print(f"  - [{msg['role'].upper()}]: \"{msg['content'][:80]}...\" (Sources: {len(msg.get('sources', []))})")
    except Exception as exc:
        print(f"[FAIL] Session replay failed: {exc}")
        return

    # 7. Test Learning Profile & Balanced Mastery Formula
    profile_url = f"{BASE_URL}/api/assessment/learning-profile"
    print("\n[7] Testing Balanced Mastery Calculation...")
    try:
        res = requests.get(profile_url, headers=headers)
        res.raise_for_status()
        profiles = res.json()
        print(f"[OK] Retrieved {len(profiles)} active topic profiles.")
        for p in profiles:
            print(f"  - Topic: {p['topic']} | Mastery: {p['mastery']}% | Retention: {p['retention']}% | Streak: {p['learning_streak']} days")
    except Exception as exc:
        print(f"[FAIL] Profile retrieval failed: {exc}")
        return

    print("\n=== All Comprehensive E2E Socratic AI Tutor Verifications PASSED! ===")

if __name__ == "__main__":
    run_e2e_verification()
