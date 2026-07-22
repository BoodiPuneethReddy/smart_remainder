import sys
import os
import requests
import json
import io

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"

def run_phase3_verification():
    print("==========================================================")
    print("      PHASE 3 — SMART ACADEMIC IMPORT VERIFICATION SUITE  ")
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
            record_test("Auth for Phase 3 Import Test", True, "Successfully logged in as alex.morgan@student.edu")
        else:
            record_test("Auth for Phase 3 Import Test", False, f"Login failed: {r.status_code}")
            return results
    except Exception as e:
        record_test("Auth for Phase 3 Import Test", False, f"Exception: {e}")
        return results

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Capabilities
    cap_url = f"{BASE_URL}/api/import/capabilities"
    try:
        r = requests.get(cap_url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            record_test("Import Capabilities Check", True, f"PDF: {data.get('pdf')}, Image OCR: {data.get('image')}", f"OCR Msg: {data.get('ocr_message')[:60] if data.get('ocr_message') else 'Available'}")
        else:
            record_test("Import Capabilities Check", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Import Capabilities Check", False, f"Exception: {e}")

    # 3. Reject Unsupported File Extension (.exe)
    upload_url = f"{BASE_URL}/api/import/upload"
    try:
        files = {'file': ('malicious.exe', b'binary content', 'application/x-msdownload')}
        r = requests.post(upload_url, files=files, headers=headers)
        if r.status_code == 400:
            record_test("Security - File Extension Filter (.exe)", True, "Correctly rejected unsupported .exe file with HTTP 400", f"Response: {r.json().get('detail')}")
        else:
            record_test("Security - File Extension Filter (.exe)", False, f"Expected HTTP 400, got {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Security - File Extension Filter (.exe)", False, f"Exception: {e}")

    # 4. Image Upload Degradation Check
    try:
        files = {'file': ('timetable.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...', 'image/png')}
        r = requests.post(upload_url, files=files, headers=headers)
        if r.status_code in [400, 200]:
            record_test("Graceful Degradation - Image OCR Handling", True, f"Handled image upload gracefully with HTTP {r.status_code}", f"Detail: {r.json().get('detail') if r.status_code == 400 else 'OCR Processed'}")
        else:
            record_test("Graceful Degradation - Image OCR Handling", False, f"Unexpected response {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Graceful Degradation - Image OCR Handling", False, f"Exception: {e}")

    # 5. PDF Upload & Smart Extraction Preview
    sample_pdf_text = """
    DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING
    COURSE SYLLABUS & ASSESSMENT SCHEDULE
    Subject: Database Management Systems (CS301)
    
    Exam 1: Mid-Term Theory Exam
    Date: 2026-08-15
    Weightage: 30%
    Topics: ER Modeling, Relational Algebra, SQL Queries
    
    Assignment 1: Relational Schema Design & Normalization
    Due Date: 2026-08-22
    Weightage: 20%
    """
    
    import_id = None
    preview_sections = []
    try:
        files = {'file': ('DBMS_Syllabus_2026.pdf', sample_pdf_text.encode('utf-8'), 'application/pdf')}
        r = requests.post(upload_url, files=files, headers=headers)
        if r.status_code == 200:
            data = r.json()
            import_id = data.get("import_id")
            preview_sections = data.get("sections", [])
            record_test("PDF Upload & Extraction Preview", True, f"Parsed PDF (Import ID: {import_id}, Doc Type: {data.get('document_type')})", f"Confidence: {data.get('classification_confidence')}, Sections: {len(preview_sections)}")
        else:
            record_test("PDF Upload & Extraction Preview", False, f"Upload failed: HTTP {r.status_code} {r.text}")
    except Exception as e:
        record_test("PDF Upload & Extraction Preview", False, f"Exception: {e}")

    # 6. Approve Import & Task Creation (Stage 2)
    if import_id:
        approve_url = f"{BASE_URL}/api/import/approve"
        reviewed_sections = []
        for s in preview_sections:
            fields_list = s.get("fields") or []
            fields_dict = {f["field_name"]: f["value"] for f in fields_list} if isinstance(fields_list, list) else {}
            reviewed_sections.append({
                "document_type": s.get("document_type", "assignment"),
                "fields": fields_dict
            })
            
        try:
            approve_body = {
                "import_id": import_id,
                "reviewed_sections": reviewed_sections
            }
            r = requests.post(approve_url, json=approve_body, headers=headers)
            if r.status_code == 200:
                res_data = r.json()
                record_test("Approve Import & Task Creation", True, f"Tasks created: {res_data.get('tasks_created')}", f"AI Summary: {res_data.get('summary', '')[:80]}...")
            else:
                record_test("Approve Import & Task Creation", False, f"Approve failed HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test("Approve Import & Task Creation", False, f"Exception: {e}")
    else:
        record_test("Approve Import & Task Creation", False, "Skipped due to missing import_id")

    # 7. Document Import History (/api/import/history)
    history_url = f"{BASE_URL}/api/import/history"
    try:
        r = requests.get(history_url, headers=headers)
        if r.status_code == 200:
            docs = r.json()
            record_test("Import History Verification", True, f"Found {len(docs)} imported document records for user", f"Recent doc: {docs[0].get('original_filename') if docs else 'None'}")
        else:
            record_test("Import History Verification", False, f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        record_test("Import History Verification", False, f"Exception: {e}")

    # 8. Source File Access (/api/import/{import_id}/source)
    if import_id:
        file_url = f"{BASE_URL}/api/import/{import_id}/source"
        try:
            r = requests.get(file_url, headers=headers)
            if r.status_code == 200:
                record_test("Source File Traceability Access", True, f"Retrieved original file content ({len(r.content)} bytes)", f"Content-Type: {r.headers.get('Content-Type')}")
            else:
                record_test("Source File Traceability Access", False, f"HTTP {r.status_code}: {r.text}")
        except Exception as e:
            record_test("Source File Traceability Access", False, f"Exception: {e}")
    else:
        record_test("Source File Traceability Access", False, "Skipped due to missing import_id")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 3 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase3_verification()
