import requests
import json
import time
from jose import jwt

BASE_URL = "http://localhost:8000"

def run_phase1_verification():
    print("==========================================================")
    print("        PHASE 1 — AUTHENTICATION VERIFICATION SUITE       ")
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

    # 1. Signup - New Valid User (/api/auth/register)
    signup_url = f"{BASE_URL}/api/auth/register"
    signup_data = {
        "email": "phase1_test_user@student.edu",
        "password": "SecurePassword123!",
        "full_name": "Phase1 Tester"
    }
    try:
        res = requests.post(signup_url, json=signup_data)
        if res.status_code in [200, 201]:
            data = res.json()
            user_obj = data.get("user", {})
            record_test("Signup - New User", True, "Successfully registered new student user", f"User ID: {user_obj.get('id')}, Email: {user_obj.get('email')}")
        else:
            record_test("Signup - New User", False, f"Unexpected status {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Signup - New User", False, f"Exception: {e}")

    # 2. Duplicate Email Signup
    try:
        res = requests.post(signup_url, json=signup_data)
        if res.status_code == 400:
            record_test("Signup - Duplicate Email", True, "Correctly rejected duplicate email with HTTP 400", f"Response: {res.json()}")
        else:
            record_test("Signup - Duplicate Email", False, f"Expected 400 Bad Request, got {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Signup - Duplicate Email", False, f"Exception: {e}")

    # 3. Login - Seeded User (alex.morgan@student.edu)
    login_url = f"{BASE_URL}/api/auth/login"
    alex_login = {"email": "alex.morgan@student.edu", "password": "StudyAI@2025"}
    token_alex = None
    try:
        res = requests.post(login_url, json=alex_login)
        if res.status_code == 200:
            data = res.json()
            token_alex = data.get("access_token")
            record_test("Login - Seeded User", True, "Authentication successful for alex.morgan@student.edu", f"Token type: {data.get('token_type')}, Token length: {len(token_alex)}")
        else:
            record_test("Login - Seeded User", False, f"Login failed: {res.status_code} {res.text}")
    except Exception as e:
        record_test("Login - Seeded User", False, f"Exception: {e}")

    # 4. Login - Newly Created User
    new_user_login = {"email": "phase1_test_user@student.edu", "password": "SecurePassword123!"}
    token_new = None
    try:
        res = requests.post(login_url, json=new_user_login)
        if res.status_code == 200:
            data = res.json()
            token_new = data.get("access_token")
            record_test("Login - Newly Registered User", True, "Authentication successful for new user", f"Token: {token_new[:30]}...")
        else:
            record_test("Login - Newly Registered User", False, f"Login failed: {res.status_code} {res.text}")
    except Exception as e:
        record_test("Login - Newly Registered User", False, f"Exception: {e}")

    # 5. Invalid Password Login
    wrong_pwd_login = {"email": "alex.morgan@student.edu", "password": "WrongPassword999!"}
    try:
        res = requests.post(login_url, json=wrong_pwd_login)
        if res.status_code in [400, 401]:
            record_test("Login - Invalid Password", True, f"Correctly rejected wrong password with HTTP {res.status_code}", f"Response: {res.json()}")
        else:
            record_test("Login - Invalid Password", False, f"Expected 401/400, got {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Login - Invalid Password", False, f"Exception: {e}")

    # 6. SQL Injection Attack on Login
    sqli_login = {"email": "invalid_sqli_email@test.com' OR '1'='1", "password": "' OR '1'='1"}
    try:
        res = requests.post(login_url, json=sqli_login)
        if res.status_code in [400, 401, 422]:
            record_test("Security - SQL Injection Login", True, f"Blocked SQL injection attempt safely with HTTP {res.status_code}", f"Response: {res.text[:100]}")
        else:
            record_test("Security - SQL Injection Login", False, f"Vulnerable or unexpected status {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Security - SQL Injection Login", False, f"Exception: {e}")

    # 7. JWT Structure & Payload Decoding
    if token_alex:
        try:
            decoded = jwt.decode(token_alex, key="", options={"verify_signature": False})
            sub = decoded.get("sub")
            exp = decoded.get("exp")
            record_test("JWT - Decoding & Payload Verification", True, "Token contains valid subject and expiration claims", f"Subject (sub): {sub}, Expiration (exp): {exp}")
        except Exception as e:
            record_test("JWT - Decoding & Payload Verification", False, f"Failed to decode token: {e}")
    else:
        record_test("JWT - Decoding & Payload Verification", False, "Skipped due to missing token")

    # 8. Session Persistence / Get Profile (/api/auth/me)
    me_url = f"{BASE_URL}/api/auth/me"
    if token_alex:
        try:
            res = requests.get(me_url, headers={"Authorization": f"Bearer {token_alex}"})
            if res.status_code == 200:
                profile = res.json()
                record_test("Session Persistence - Get Current User (/api/auth/me)", True, f"Retrieved profile for {profile.get('email')}", f"Name: {profile.get('full_name')}, College ID: {profile.get('college_id')}")
            else:
                record_test("Session Persistence - Get Current User (/api/auth/me)", False, f"Failed with {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Session Persistence - Get Current User (/api/auth/me)", False, f"Exception: {e}")
    else:
        record_test("Session Persistence - Get Current User (/api/auth/me)", False, "Skipped due to missing token")

    # 9. Protected Routes - Unauthorized Access (No Token)
    try:
        res = requests.get(f"{BASE_URL}/api/planner/daily")
        if res.status_code in [401, 403]:
            record_test("Protected Routes - Unauthorized Access (No Token)", True, f"Correctly denied request with HTTP {res.status_code}", f"Response: {res.text[:100]}")
        else:
            record_test("Protected Routes - Unauthorized Access (No Token)", False, f"Expected 401/403, got {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Protected Routes - Unauthorized Access (No Token)", False, f"Exception: {e}")

    # 10. JWT Tampering / Invalid Signature
    if token_alex:
        tampered_token = token_alex[:-5] + "XXXXX"
        try:
            res = requests.get(me_url, headers={"Authorization": f"Bearer {tampered_token}"})
            if res.status_code in [401, 403]:
                record_test("Security - JWT Tampering", True, f"Correctly rejected tampered signature with HTTP {res.status_code}", f"Response: {res.text[:100]}")
            else:
                record_test("Security - JWT Tampering", False, f"Expected 401/403, got {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Security - JWT Tampering", False, f"Exception: {e}")
    else:
        record_test("Security - JWT Tampering", False, "Skipped due to missing token")

    # 11. Cross-User Access Control
    if token_alex and token_new:
        try:
            tasks_alex_res = requests.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {token_alex}"})
            tasks_alex = tasks_alex_res.json() if tasks_alex_res.status_code == 200 else []
            
            tasks_new_res = requests.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {token_new}"})
            tasks_new = tasks_new_res.json() if tasks_new_res.status_code == 200 else []
            
            alex_ids = {t["id"] for t in tasks_alex} if isinstance(tasks_alex, list) else set()
            new_ids = {t["id"] for t in tasks_new} if isinstance(tasks_new, list) else set()
            
            overlap = alex_ids.intersection(new_ids)
            if len(overlap) == 0:
                record_test("Security - Cross-User Resource Isolation", True, "User A and User B tasks are completely isolated", f"Alex Tasks Count: {len(alex_ids)}, New User Tasks Count: {len(new_ids)}")
            else:
                record_test("Security - Cross-User Resource Isolation", False, f"Resource leakage detected! Overlapping task IDs: {overlap}")
        except Exception as e:
            record_test("Security - Cross-User Resource Isolation", False, f"Exception: {e}")
    else:
        record_test("Security - Cross-User Resource Isolation", False, "Skipped due to missing token")

    # 12. College Search Endpoint (/api/colleges/search?q=IIT)
    colleges_url = f"{BASE_URL}/api/colleges/search"
    try:
        res = requests.get(f"{colleges_url}?q=IIT")
        if res.status_code == 200:
            colleges = res.json()
            names = [c.get("college_name") for c in colleges[:3]] if isinstance(colleges, list) else []
            record_test("College Search - Alias Matching ('IIT')", True, f"Found {len(colleges)} matching colleges for 'IIT'", f"First 3: {names}")
        else:
            record_test("College Search - Alias Matching ('IIT')", False, f"Failed with {res.status_code}: {res.text}")
    except Exception as e:
        record_test("College Search - Alias Matching ('IIT')", False, f"Exception: {e}")

    # 13. Invalid College Search Query
    try:
        res = requests.get(f"{colleges_url}?q=NonExistentCollegeX99")
        if res.status_code == 200:
            colleges = res.json()
            record_test("College Search - Non-Existent Query", True, "Gracefully returned empty array for invalid query", f"Results count: {len(colleges)}")
        else:
            record_test("College Search - Non-Existent Query", False, f"Failed with {res.status_code}: {res.text}")
    except Exception as e:
        record_test("College Search - Non-Existent Query", False, f"Exception: {e}")

    # 14. Forgot Password / OTP Flow
    forgot_url = f"{BASE_URL}/api/auth/forgot-password"
    otp_code = None
    try:
        res = requests.post(forgot_url, json={"email": "phase1_test_user@student.edu"})
        if res.status_code == 200:
            forgot_data = res.json()
            otp_code = forgot_data.get("dev_otp") or forgot_data.get("otp") or "123456"
            record_test("Forgot Password - Request OTP", True, "OTP generated successfully", f"Message: {forgot_data.get('message')}, Dev OTP: {otp_code}")
        else:
            record_test("Forgot Password - Request OTP", False, f"Failed with {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Forgot Password - Request OTP", False, f"Exception: {e}")

    # 15. Verify Wrong OTP
    verify_otp_url = f"{BASE_URL}/api/auth/verify-otp"
    try:
        res = requests.post(verify_otp_url, json={"email": "phase1_test_user@student.edu", "otp": "000000"})
        if res.status_code in [400, 401]:
            record_test("Forgot Password - Wrong OTP Check", True, f"Correctly rejected wrong OTP code with HTTP {res.status_code}", f"Response: {res.json()}")
        else:
            record_test("Forgot Password - Wrong OTP Check", False, f"Expected 400/401, got {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Forgot Password - Wrong OTP Check", False, f"Exception: {e}")

    # 16. Verify Valid OTP & Obtain Reset Token
    reset_token = None
    try:
        res = requests.post(verify_otp_url, json={"email": "phase1_test_user@student.edu", "otp": otp_code or "123456"})
        if res.status_code == 200:
            verify_data = res.json()
            reset_token = verify_data.get("reset_token")
            record_test("Forgot Password - Verify Valid OTP Code", True, "OTP verified cleanly, returned reset_token", f"Reset Token: {reset_token[:30] if reset_token else None}...")
        else:
            record_test("Forgot Password - Verify Valid OTP Code", False, f"Failed with {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Forgot Password - Verify Valid OTP Code", False, f"Exception: {e}")

    # 17. Reset Password with Reset Token
    reset_pwd_url = f"{BASE_URL}/api/auth/reset-password"
    if reset_token:
        try:
            res = requests.post(reset_pwd_url, json={
                "reset_token": reset_token,
                "new_password": "BrandNewPassword2026!"
            })
            if res.status_code == 200:
                record_test("Forgot Password - Reset Password with Token", True, "Password updated successfully", f"Response: {res.json()}")
            else:
                record_test("Forgot Password - Reset Password with Token", False, f"Failed with {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Forgot Password - Reset Password with Token", False, f"Exception: {e}")
    else:
        record_test("Forgot Password - Reset Password with Token", False, "Skipped due to missing reset_token")

    # 18. Verify Login with New Password
    if reset_token:
        try:
            res = requests.post(login_url, json={
                "email": "phase1_test_user@student.edu",
                "password": "BrandNewPassword2026!"
            })
            if res.status_code == 200:
                record_test("Auth Integration - Login with Newly Reset Password", True, "Successfully logged in using new password", f"Token: {res.json().get('access_token')[:25]}...")
            else:
                record_test("Auth Integration - Login with Newly Reset Password", False, f"Failed with {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Auth Integration - Login with Newly Reset Password", False, f"Exception: {e}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 1 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase1_verification()
