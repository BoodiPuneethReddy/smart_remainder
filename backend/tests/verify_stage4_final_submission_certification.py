import os
import sys
import unittest
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from tests.test_permanent_academic_import_regression_suite import TestPermanentAcademicImportRegressionSuite
from tests.verify_stage3_cross_reference_check import verify_stage3_cross_reference_check

BASE_URL = "http://localhost:8000"

def run_stage4_final_certification():
    print("================================================================================")
    print("      STAGE 4: FINAL SYSTEM AUDIT & HACKATHON SUBMISSION CERTIFICATION          ")
    print("================================================================================")

    # 1. Verify User Account & College
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "punithgodof@gmail.com", "password": "Punith@123"})
    assert r_login.status_code == 200, f"Account verification failed: {r_login.text}"
    token = r_login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    r_me = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    assert r_me.status_code == 200, f"User profile check failed: {r_me.text}"
    user_info = r_me.json()
    print(f"[PASS] 1. Account Verified: {user_info.get('email')} | College: {user_info.get('college')}")
    assert user_info.get("email") == "punithgodof@gmail.com", "Incorrect primary account email!"
    assert user_info.get("college") in ["SVCE", "Sri Venkateswara College of Engineering"], f"College field unexpected: {user_info.get('college')}"

    # 2. Run Permanent Regression Test Suite (10/10 Tests)
    print("\n--- Running Permanent Regression Test Suite (10 Tests) ---")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPermanentAcademicImportRegressionSuite)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    assert result.wasSuccessful(), "Permanent Regression Test Suite failed!"
    print("[PASS] 2. Permanent Regression Test Suite PASSED CLEANLY (10/10 PASS)!")

    # 3. Run Stage 3 Cross-Reference Check
    print("\n--- Running Stage 3 Cross-Reference Grounding Test ---")
    verify_stage3_cross_reference_check()
    print("[PASS] 3. Stage 3 Cross-Reference Grounding Test PASSED CLEANLY!")

    # 4. Verify Active Services
    print("\n--- Checking Live Server Services ---")
    r_health = requests.get(f"{BASE_URL}/health")
    assert r_health.status_code == 200, "Backend health check failed!"
    print("[PASS] 4. Backend Health Endpoint: OK")

    print("\n================================================================================")
    print(" [PASS] STAGE 4 FINAL HACKATHON SUBMISSION CERTIFIED PROVABLY AT RUNTIME!      ")
    print("================================================================================")

if __name__ == "__main__":
    run_stage4_final_certification()
