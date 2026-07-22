"""
verify_otp_behavior.py — Programmatically validates Forgot Password & OTP banner behavior
"""

import requests
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")

def main():
    print_section("1. Search SVCE College & Register a Test User")
    
    # Get SVCE college ID
    colleges = requests.get(f"{BASE_URL}/api/colleges/search?q=SVCE&limit=1").json()
    college_id = colleges[0]['id']
    
    email = "alex.morgan.real@gmail.com"
    reg_data = {
        "email": email,
        "full_name": "Alex Morgan",
        "password": "TestPassword123",
        "college_id": college_id,
        "date_of_birth": "2000-01-01"
    }
    
    # Try registering, ignore if already exists
    reg_res = requests.post(f"{BASE_URL}/api/auth/register", json=reg_data)
    print(f"Register status: {reg_res.status_code}")
    
    # ── Test Scenario 1: Registered Email with SMTP Success ──────────────────
    print_section("Test Scenario 1: Registered Email (Real SMTP sending works)")
    # Since SMTP_HOST & SMTP_USERNAME are configured in our local .env, this will trigger smtplib.
    # It will successfully connect and dispatch the mail, and therefore return no dev_otp!
    forgot_res = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email})
    print(f"Forgot password status: {forgot_res.status_code}")
    forgot_data = forgot_res.json()
    print("Response payload:")
    for k, v in forgot_data.items():
        print(f"  {k}: {v}")
    
    # VERIFY dev_otp is omitted
    if "dev_otp" in forgot_data:
        print("[FAILED] FAILED: dev_otp was returned even though email was successfully sent!")
        sys.exit(1)
    else:
        print("[PASSED] PASSED: dev_otp was omitted when email sent successfully!")

    # ── Test Scenario 2: Unregistered Email ─────────────────────────────────
    print_section("Test Scenario 2: Unregistered Email (Should return 404 & correct error message)")
    unreg_email = "unregistered_random_user_12345@gmail.com"
    unreg_res = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": unreg_email})
    print(f"Status code received: {unreg_res.status_code}")
    unreg_data = unreg_res.json()
    print(f"Detail payload: {unreg_data.get('detail')}")
    
    # VERIFY it returns 404 and stay on page details
    if unreg_res.status_code == 404 and "No account found" in unreg_data.get('detail', ''):
        print("[PASSED] PASSED: Correct 404 and error message returned for unregistered email!")
    else:
        print("[FAILED] FAILED: Incorrect status code or message for unregistered email!")
        sys.exit(1)

    print_section("E2E OTP Behavior Verification Completely Successful!")

if __name__ == "__main__":
    main()
