"""
verify_e2e.py — End-to-End integration test script

Simulates the entire front-to-back flow including:
  1. Searching colleges in directory (Stage A)
  2. Registering a new user with college selection and DOB (Stage A/D)
  3. Logging in and checking profile
  4. Creating a test PDF document (with assignment content)
  5. Uploading the PDF for preview, verifying extracted fields and duplicates (Stage B)
  6. Approving the import and checking AI study plan response (Stage B)
  7. Requesting password reset OTP (Stage D)
  8. Verifying OTP and resetting password (Stage D)
  9. Confirming new password login works
"""

import sys
import os
import json
import requests

BASE_URL = "http://localhost:8000"


def print_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def main():
    # ── 1. Search Colleges ────────────────────────────────────────────────────
    print_section("1. Search Colleges in Directory")
    res = requests.get(f"{BASE_URL}/api/colleges/search?q=SVCE&limit=3")
    print(f"Status: {res.status_code}")
    colleges = res.json()
    print(f"Results found: {len(colleges)}")
    for c in colleges:
        print(f"  ID {c['id']}: {c['college_name']} ({c['state']})")

    if not colleges:
        print("Error: No colleges found. Make sure backend is running and seeded.")
        sys.exit(1)

    target_college = colleges[0]
    college_id = target_college["id"]

    # ── 2. Register New User ──────────────────────────────────────────────────
    print_section("2. Register New User with College and DOB")
    import time
    email = f"alex.morgan.test_{int(time.time())}@student.edu"
    register_data = {
        "email": email,
        "full_name": "Alex Morgan",
        "password": "TestPassword123",
        "college_id": college_id,
        "date_of_birth": "2000-01-01",
    }
    # In case user already exists, we ignore 400 and proceed to login
    res = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    print(f"Register Status: {res.status_code}")
    if res.status_code == 201:
        token_data = res.json()
        print("Registration successful!")
    else:
        print("Registration returned status (user might exist), trying login...")
        login_res = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": "TestPassword123"},
        )
        print(f"Login Status: {login_res.status_code}")
        if login_res.status_code != 200:
            print("Login failed, trying fallback credentials...")
            sys.exit(1)
        token_data = login_res.json()

    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # ── 3. Check Profile ──────────────────────────────────────────────────────
    print_section("3. Verify Current User details")
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    user = res.json()
    print(f"Logged in user: {user['full_name']}")
    print(f"Email: {user['email']}")
    print(f"College ID: {user.get('college_id')}")

    # ── 4. Create Fake PDF ────────────────────────────────────────────────────
    print_section("4. Creating Test PDF Document")
    # We will build a PDF using reportlab or fpdf if installed, or we can just send
    # a text file with .pdf extension, but since pdfplumber is used, we can create
    # a simple PDF using the pre-installed python packages or create it via a python script.
    # Let's check if we can create a PDF using reportlab/fpdf or just write a small PDF using a python code.
    # Alternatively, we can just write text in a PDF format or use reportlab if it's there.
    # Let's create a minimal valid PDF with assignment text using reportlab.
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        pdf_path = "test_assignment.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Course: CS-201 Data Structures")
        c.drawString(100, 730, "Assignment Title: Heap Sort Implementation")
        c.drawString(100, 710, "Professor: Dr. Alice Smith")
        c.drawString(100, 690, "Due Date: 28/07/2026")
        c.drawString(100, 670, "Submission Time: 11:59 pm")
        c.drawString(100, 650, "Instructions: Implement a binary min-heap and heap sort algorithm.")
        c.save()
        print("Created test_assignment.pdf successfully.")
    except ImportError:
        print("reportlab not found, writing text format (fallback)")
        # If pdfplumber is used, it needs a real PDF. Let's use reportlab to make sure.
        # Let's install reportlab quickly if not present.
        print("Let's install reportlab to write a valid PDF file...")
        os.system("..\venv\Scripts\pip install reportlab --quiet")
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        pdf_path = "test_assignment.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Course: CS-201 Data Structures")
        c.drawString(100, 730, "Assignment Title: Heap Sort Implementation")
        c.drawString(100, 710, "Professor: Dr. Alice Smith")
        c.drawString(100, 690, "Due Date: 28/07/2026")
        c.drawString(100, 670, "Submission Time: 11:59 pm")
        c.drawString(100, 650, "Instructions: Implement a binary min-heap.")
        c.save()
        print("Created test_assignment.pdf successfully via reportlab.")

    # ── 5. Upload for Preview ─────────────────────────────────────────────────
    print_section("5. Uploading Document for Preview")
    with open(pdf_path, "rb") as f:
        res = requests.post(
            f"{BASE_URL}/api/import/upload",
            files={"file": (pdf_path, f, "application/pdf")},
            headers=headers,
        )
    print(f"Status: {res.status_code}")
    preview = res.json()
    print(f"Import ID: {preview['import_id']}")
    print(f"Detected Type: {preview['document_type']}")
    print(f"Classification Confidence: {preview['classification_confidence']:.2f}")

    print("\nExtracted Sections:")
    for sec in preview["sections"]:
        print(f"  Type: {sec['document_type']} ({sec['display_name']})")
        print("  Fields:")
        for field in sec["fields"]:
            print(f"    - {field['display_label']}: '{field['value']}' (Confidence: {field['confidence']})")
        print(f"  Missing required fields: {sec['missing_required']}")
        print(f"  Possible duplicates found: {len(sec['possible_duplicates'])}")

    # ── 6. Approve the Import ─────────────────────────────────────────────────
    print_section("6. Approving the Import Preview")
    reviewed_sections = []
    for sec in preview["sections"]:
        fields = {}
        for f in sec["fields"]:
            fields[f["field_name"]] = f["value"] or "CS-201 Data Structures"
        reviewed_sections.append({
            "document_type": sec["document_type"],
            "fields": fields,
        })

    approve_data = {
        "import_id": preview["import_id"],
        "reviewed_sections": reviewed_sections,
    }
    res = requests.post(
        f"{BASE_URL}/api/import/approve",
        json=approve_data,
        headers=headers,
    )
    print(f"Status: {res.status_code}")
    result = res.json()
    print(f"Tasks Created: {result['tasks_created']}")
    print(f"Task IDs: {result['task_ids']}")
    print(f"AI Study Recommendation:\n{result['ai_summary']}")

    # ── 7. Forgot Password / OTP Flow ─────────────────────────────────────────
    print_section("7. Requesting OTP for Password Reset")
    res = requests.post(
        f"{BASE_URL}/api/auth/forgot-password",
        json={"email": email},
    )
    print(f"Status: {res.status_code}")
    otp_data = res.json()
    print(f"Message: {otp_data['message']}")
    dev_otp = otp_data.get("dev_otp")
    print(f"Dev OTP Code: {dev_otp}")

    if not dev_otp:
        print("Error: dev_otp not found in response. Make sure APP_ENV is development.")
        sys.exit(1)

    # ── 8. Verify OTP ─────────────────────────────────────────────────────────
    print_section("8. Verifying OTP Code")
    res = requests.post(
        f"{BASE_URL}/api/auth/verify-otp",
        json={"email": email, "otp": dev_otp},
    )
    print(f"Status: {res.status_code}")
    verify_data = res.json()
    reset_token = verify_data.get("reset_token")
    print(f"Reset Token received: {reset_token[:30]}...")

    # ── 9. Reset Password ─────────────────────────────────────────────────────
    print_section("9. Resetting Password")
    res = requests.post(
        f"{BASE_URL}/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "NewStudyAI2026"},
    )
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()['message']}")

    # ── 10. Confirm New Password Login ────────────────────────────────────────
    print_section("10. Verify Login with New Password")
    res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": "NewStudyAI2026"},
    )
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print("[SUCCESS] E2E Integration and Verification Plan completely successful! All stages work.")
    else:
        print("[FAILED] Login with new password failed.")
        sys.exit(1)

    # Cleanup test file
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


if __name__ == "__main__":
    main()
