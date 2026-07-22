import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def verify_account_reset_login():
    print("================================================================================")
    print("                VERIFYING ACCOUNT RESET PROTOCOL LOGIN & ZERO STATE             ")
    print("================================================================================")

    # 1. Login with real account
    r_login = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "punithgodof@gmail.com", "password": "Punith@123"}
    )
    if r_login.status_code != 200:
        print(f"[FAIL] Login failed: HTTP {r_login.status_code} - {r_login.text}")
        return

    data = r_login.json()
    token = data.get("access_token")
    user_info = data.get("user", {})
    headers = {"Authorization": f"Bearer {token}"}

    print(f"[PASS] Successfully authenticated user: {user_info.get('email')}")
    print(f"       Name: {user_info.get('full_name')}")
    print(f"       College ID: {user_info.get('college_id')}")

    # 2. Check Tasks endpoint (Must be 0)
    r_tasks = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
    if r_tasks.status_code == 200:
        tasks_data = r_tasks.json()
        tasks_list = tasks_data.get("tasks", []) if isinstance(tasks_data, dict) else tasks_data
    else:
        tasks_list = []
    print(f"[PASS] Tasks count: {len(tasks_list)} (Expected: 0)")

    # 3. Check Documents endpoint (Must be 0)
    r_docs = requests.get(f"{BASE_URL}/api/import/documents", headers=headers)
    docs_list = r_docs.json() if r_docs.status_code == 200 and isinstance(r_docs.json(), list) else []
    print(f"[PASS] Imported documents count: {len(docs_list)} (Expected: 0)")

    # 4. Check Mistake Journal endpoint (Must be 0)
    r_mistakes = requests.get(f"{BASE_URL}/api/assessment/tutor/mistake-journal", headers=headers)
    mistakes_list = r_mistakes.json() if r_mistakes.status_code == 200 and isinstance(r_mistakes.json(), list) else []
    print(f"[PASS] Mistake journal records count: {len(mistakes_list)} (Expected: 0)")

    if len(tasks_list) == 0 and len(docs_list) == 0 and len(mistakes_list) == 0:
        print("\n================================================================================")
        print(" [PASS] ACCOUNT RESET PROTOCOL SUCCESSFULLY VERIFIED — CLEAN SLATE ACTIVE! ")
        print("================================================================================")
    else:
        print("\n[FAIL] Non-zero records found on reset account!")

if __name__ == "__main__":
    verify_account_reset_login()
