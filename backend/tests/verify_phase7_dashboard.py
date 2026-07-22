import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def run_phase7_verification():
    print("==========================================================")
    print("           PHASE 7 — DASHBOARD WIDGETS SUITE              ")
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
            record_test("Auth for Phase 7 Dashboard Tests", True, "Successfully logged in as alex.morgan@student.edu")
        else:
            record_test("Auth for Phase 7 Dashboard Tests", False, f"Login failed: {r.status_code}")
            return results
    except Exception as e:
        record_test("Auth for Phase 7 Dashboard Tests", False, f"Exception: {e}")
        return results

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Today's Plan Card & Priority Tasks (/api/planner/daily)
    try:
        r = requests.get(f"{BASE_URL}/api/planner/daily", headers=headers)
        if r.status_code == 200:
            plan = r.json()
            tasks = plan.get("tasks", [])
            record_test("Widget: Today's Plan Card", True, f"Returned {len(tasks)} prioritized study tasks for today", f"Total Mins: {plan.get('total_study_minutes')}, First Task: {tasks[0].get('title') if tasks else 'None'}")
        else:
            record_test("Widget: Today's Plan Card", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Today's Plan Card", False, f"Exception: {e}")

    # 3. Completion %, Study Hours & Streak Stats (/api/analytics/summary)
    try:
        r = requests.get(f"{BASE_URL}/api/analytics/summary", headers=headers)
        if r.status_code == 200:
            summary = r.json()
            record_test("Widget: Stat Cards (Completion, Hours, Streak)", True, f"Completion: {summary.get('completion_rate')}%, Hours: {summary.get('total_study_hours')}, Streak: {summary.get('current_streak')} days", f"Total Tasks: {summary.get('total_tasks')}, Completed: {summary.get('completed_tasks')}")
        else:
            record_test("Widget: Stat Cards (Completion, Hours, Streak)", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Stat Cards (Completion, Hours, Streak)", False, f"Exception: {e}")

    # 4. Weekly Activity Bar Chart (/api/analytics/weekly)
    try:
        r = requests.get(f"{BASE_URL}/api/analytics/weekly", headers=headers)
        if r.status_code == 200:
            weekly = r.json()
            record_test("Widget: Weekly Activity Bar Chart", True, f"Returned {len(weekly.get('days', []))} daily activity data points", f"Weekly Total Mins: {weekly.get('total_minutes')}")
        else:
            record_test("Widget: Weekly Activity Bar Chart", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Weekly Activity Bar Chart", False, f"Exception: {e}")

    # 5. Knowledge Map & Learning Profiles (/api/assessment/learning-profile)
    try:
        r = requests.get(f"{BASE_URL}/api/assessment/learning-profile", headers=headers)
        if r.status_code == 200:
            profiles = r.json()
            record_test("Widget: Knowledge Map Tree", True, f"Returned {len(profiles)} tracked topic profiles", f"First Topic: {profiles[0].get('topic') if profiles else 'None'}, Mastery: {profiles[0].get('mastery') if profiles else '0'}%")
        else:
            record_test("Widget: Knowledge Map Tree", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Knowledge Map Tree", False, f"Exception: {e}")

    # 6. Mistake Journal (/api/assessment/tutor/mistake-journal)
    try:
        r = requests.get(f"{BASE_URL}/api/assessment/tutor/mistake-journal", headers=headers)
        if r.status_code == 200:
            journal = r.json()
            record_test("Widget: Mistake Journal Records", True, f"Retrieved {len(journal)} recorded student misconceptions", f"Journal Array: {type(journal).__name__}")
        else:
            record_test("Widget: Mistake Journal Records", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Mistake Journal Records", False, f"Exception: {e}")

    # 7. Source Syllabus Coverage (/api/import/history)
    try:
        r = requests.get(f"{BASE_URL}/api/import/history", headers=headers)
        if r.status_code == 200:
            history = r.json()
            record_test("Widget: Uploaded Sources Coverage", True, f"Retrieved {len(history)} uploaded academic source documents", f"Recent File: {history[0].get('original_filename') if history else 'None'}")
        else:
            record_test("Widget: Uploaded Sources Coverage", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Widget: Uploaded Sources Coverage", False, f"Exception: {e}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 7 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase7_verification()
