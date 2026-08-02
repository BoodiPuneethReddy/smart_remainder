"""
tests/test_otp_auth.py — Integration test suite for OTP Generation, SMTP Email Helper, and Verification
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.otp_code import OTPCode
from app.core.security import hash_password, verify_password
from app.api.routes.auth import _generate_otp, _send_otp_email, get_settings


client = TestClient(app)


def test_generate_otp_format():
    otp = _generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_otp_forgot_verify_and_reset_flow():
    db = SessionLocal()
    # Create test user
    email = "otp_test_user_2026@example.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name="OTP Test User",
            hashed_password=hash_password("OldPassword123!"),
            is_active=True,
        )
        db.add(user)
        db.commit()

    # Step 1: Request Forgot Password
    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert "message" in data
    assert "dev_otp" in data
    dev_otp = data["dev_otp"]

    # Verify OTP saved in DB
    otp_record = (
        db.query(OTPCode)
        .filter(OTPCode.email == email, OTPCode.used == False)
        .order_by(OTPCode.created_at.desc())
        .first()
    )
    assert otp_record is not None
    assert verify_password(dev_otp, otp_record.code_hash)

    # Step 2: Failed OTP verification attempt
    bad_res = client.post("/api/auth/verify-otp", json={"email": email, "otp": "000000"})
    assert bad_res.status_code == 400
    assert "Incorrect OTP" in bad_res.json()["detail"]

    # Step 3: Successful OTP verification
    good_res = client.post("/api/auth/verify-otp", json={"email": email, "otp": dev_otp})
    assert good_res.status_code == 200
    reset_token = good_res.json()["reset_token"]
    assert reset_token is not None

    # Step 4: Reset password
    new_pass = "NewSecurePassword123!"
    reset_res = client.post("/api/auth/reset-password", json={"reset_token": reset_token, "new_password": new_pass})
    assert reset_res.status_code == 200
    assert reset_res.json()["message"] == "Password reset successfully. Please log in with your new password."

    # Step 5: Verify login with new password
    login_res = client.post("/api/auth/login", json={"email": email, "password": new_pass})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_forgot_password_nonexistent_email():
    res = client.post("/api/auth/forgot-password", json={"email": "nonexistent_9999@example.com"})
    assert res.status_code == 404
    assert "No account found" in res.json()["detail"]


def test_smtp_email_helper_fallback():
    settings = get_settings()
    sent = _send_otp_email("test@example.com", "123456", "Test User", settings=settings)
    # Returns False if SMTP is not configured or in test mode without live SMTP host
    assert isinstance(sent, bool)
