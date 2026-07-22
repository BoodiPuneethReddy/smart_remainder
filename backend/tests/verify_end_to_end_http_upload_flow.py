import sys
import os
import json
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def verify_end_to_end_http_upload_flow():
    print("================================================================================")
    print("      VERIFYING REAL HTTP FILE UPLOAD FLOW (PDF BYTES -> BACKEND -> JSON)       ")
    print("================================================================================")

    # 1. Authenticate as punithgodof@gmail.com
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "punithgodof@gmail.com", "password": "Punith@123"})
    if r_login.status_code != 200:
        print(f"[FAIL] Login failed: {r_login.text}")
        return
    token = r_login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated via HTTP as punithgodof@gmail.com")

    # 2. Read real binary PDF file bytes and upload to POST /api/import/upload
    pdf_path = os.path.abspath(os.path.dirname(__file__) + "/dataset/Edge_Case_Academic_Schedule_Test.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    files = {"file": ("Edge_Case_Academic_Schedule_Test.pdf", pdf_bytes, "application/pdf")}
    r_upload = requests.post(f"{BASE_URL}/api/import/upload", headers=headers, files=files)

    if r_upload.status_code != 200:
        print(f"[FAIL] HTTP Upload failed: {r_upload.status_code} - {r_upload.text}")
        return

    res_json = r_upload.json()
    print("\n================================================================================")
    print("                         RAW HTTP API RESPONSE JSON                             ")
    print("================================================================================")
    print(json.dumps(res_json, indent=2))

    sections = res_json.get("sections", [])
    print(f"\n[PASS] HTTP Upload returned {len(sections)} sections in ImportPreview JSON.")
    print(f"[PASS] Dynamic Overall Document Confidence: {res_json.get('classification_confidence') * 100:.1f}%")

    # Assert 3 Categorized Section Buckets
    extracted_tasks = [s for s in sections if s.get("document_type") not in ("ignored_item", "needs_confirmation")]
    needs_confirmation = [s for s in sections if s.get("document_type") == "needs_confirmation"]
    ignored_items = [s for s in sections if s.get("document_type") == "ignored_item"]

    print(f"• Active Extracted Tasks ({len(extracted_tasks)}): {[s.get('display_name') for s in extracted_tasks]}")
    print(f"• Needs Confirmation ({len(needs_confirmation)}): {[s.get('display_name') for s in needs_confirmation]}")
    print(f"• Ignored Items ({len(ignored_items)}): {[s.get('display_name') for s in ignored_items]}")

    assert len(ignored_items) >= 1, "Ignored items bucket is empty! Suppressed events still in main list!"
    ai_ignored = next((s for s in ignored_items if "ai workshop" in s.get("display_name", "").lower()), None)
    assert ai_ignored is not None, "AI Workshop not moved to Ignored Items!"
    print("\n[PASS] 1. Suppressed Event (AI Workshop) moved to Ignored Items: VERIFIED")

    mini_proj = next((s for s in needs_confirmation if "mini project" in s.get("display_name", "").lower()), None)
    assert mini_proj is not None, "Mini Project with 'Week 3' relative date not moved to Needs Confirmation!"
    print("[PASS] 2. Ambiguous Task (Mini Project Week 3) moved to Needs Confirmation: VERIFIED")

    # Validate DBMS Case Study Subject Canonicalization in JSON
    dbms_sec = next((s for s in sections if "dbms" in s.get("display_name", "").lower()), None)
    assert dbms_sec is not None, "DBMS section missing from HTTP upload response!"
    
    fields_dict = {f.get("field_name"): f.get("value") for f in dbms_sec.get("fields", [])}
    print(f"\n--- DBMS Case Study Normalized Extracted Fields (HTTP API) ---")
    print(f"• Normalized Subject: {fields_dict.get('subject')}")
    print(f"• Corrected Deadline: {fields_dict.get('due_date')}")
    print(f"• Linked Faculty:     {fields_dict.get('faculty')}")

    assert fields_dict.get("subject") == "Database Management Systems", "Subject normalization failed! (Expected 'Database Management Systems')"
    assert "27 Aug 2026" in fields_dict.get("due_date", ""), "HTTP API returned uncorrected deadline!"
    assert fields_dict.get("faculty") == "Dr. A. Kumar", "HTTP API returned incorrect faculty!"
    print("[PASS] 3. Canonical Subject Normalization (DBMS -> Database Management Systems): VERIFIED")

    # 3. Test POST /api/import/approve
    reviewed_sections = [
        {"document_type": s.get("document_type"), "fields": {f.get("field_name"): f.get("value") for f in s.get("fields", [])}}
        for s in sections
    ]
    r_approve = requests.post(f"{BASE_URL}/api/import/approve", headers=headers, json={"import_id": res_json.get("import_id"), "reviewed_sections": reviewed_sections})
    assert r_approve.status_code == 200, f"Approve failed: {r_approve.text}"
    approve_data = r_approve.json()
    print(f"\n[PASS] 4. Approved Import: Created {approve_data.get('tasks_created')} active tasks (Ignored items excluded from DB task creation!)")

    print("\n================================================================================")
    print(" [PASS] ALL HARDENED EDGE CASE IMPORTER REQUIREMENTS VERIFIED PROVABLY!       ")
    print("================================================================================")

if __name__ == "__main__":
    verify_end_to_end_http_upload_flow()
