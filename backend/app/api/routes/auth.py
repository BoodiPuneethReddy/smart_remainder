"""
api/routes/auth.py — Authentication endpoints.

Endpoints:
  POST /api/auth/login           ← email + password → JWT token
  POST /api/auth/register        ← sign up with college_id + DOB
  GET  /api/auth/me              ← get current user
  POST /api/auth/forgot-password ← send OTP to email
  POST /api/auth/verify-otp      ← verify OTP → reset_token
  POST /api/auth/reset-password  ← set new password with reset_token

OTP in development mode:
  If APP_ENV=development (default), the OTP is returned in the API response.
  For production, configure SMTP in .env (SMTP_HOST, SMTP_USER, SMTP_PASSWORD).
  See README for setup instructions.
"""

import random
import string
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.otp_code import OTPCode
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse, UserUpdate

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)

# OTP configuration
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_LIMIT_MINUTES = 60
OTP_RESEND_LIMIT_COUNT = 3


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    college_id: Optional[int] = None
    custom_college: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    date_of_birth: Optional[date] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Generates a random 6-digit numeric string."""
    return "".join(random.choices(string.digits, k=6))


def _send_otp_email(email: str, otp: str, full_name: str, settings=None) -> bool:
    """
    Sends a formatted HTML email containing the OTP code.
    Returns True if sent successfully, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    if settings.dev_mode:
        logger.info("DEV MODE — Generated OTP for %s: %s", email, otp)

    if not settings.smtp_host or not settings.smtp_username:
        logger.warning("SMTP not configured — falling back. (host: %r)", settings.smtp_host)
        return False

    sender_email = settings.smtp_from_email or settings.smtp_username
    sender_name = settings.smtp_from_name or "Smart Study Reminder AI"

    # Plain text version for fallback
    text_content = f"""Hi {full_name},
Your 6-digit verification code is:
[ {otp} ]
This code is single-use and will expire in {OTP_TTL_MINUTES} minutes. For security, never share this code.
"""

    # HTML Version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; background-color: #0b0e14; color: #f5f7fa; padding: 20px; }}
    .container {{ max-width: 500px; margin: 0 auto; background: #0f1219; border-radius: 12px; padding: 30px; border: 1px solid #1f293d; }}
    .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 6px; color: #ff6b35; text-align: center; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #98a2b3; text-align: center; margin-top: 20px; }}
  </style>
</head>
<body>
  <div class="container">
    <h2>Reset Your Password</h2>
    <p>Hi {full_name},</p>
    <p>Please use the following 6-digit verification code to complete your reset:</p>
    <div class="otp-code">{otp}</div>
    <p style="font-size: 12px; color: #ffc857;"><strong>Notice:</strong> This code is valid for 10 minutes and can only be used once.</p>
    <div class="footer">Smart Study Reminder AI</div>
  </div>
</body>
</html>
"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Smart Study Reminder AI – Password Reset OTP"
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        port = settings.smtp_port
        if port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, port, timeout=10.0)
        else:
            server = smtplib.SMTP(settings.smtp_host, port, timeout=10.0)
            server.starttls()

        try:
            if settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
            logger.info("OTP email delivered successfully to %s", email)
            return True
        finally:
            server.quit()
    except Exception as exc:
        logger.error("SMTP delivery failed to %s: %s", email, exc)
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")
    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    if not user_data.full_name or not user_data.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate college_id if provided
    if user_data.college_id is not None:
        from app.models.college import College
        college = db.query(College).filter(College.id == user_data.college_id).first()
        if not college:
            raise HTTPException(status_code=400, detail="Invalid college selection. Please select from the directory.")

    user = User(
        email=user_data.email,
        full_name=user_data.full_name.strip(),
        hashed_password=hash_password(user_data.password),
        college_id=user_data.college_id,
        custom_college=user_data.custom_college,
        department=user_data.department,
        year=user_data.year,
        date_of_birth=user_data.date_of_birth,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
@router.patch("/me", response_model=UserResponse)
def update_profile(
    updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if updates.email and updates.email != current_user.email:
        existing = db.query(User).filter(User.email == updates.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = updates.email

    if updates.full_name is not None:
        if not updates.full_name.strip():
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        current_user.full_name = updates.full_name.strip()

    if updates.college_id is not None:
        from app.models.college import College
        college = db.query(College).filter(College.id == updates.college_id).first()
        if not college:
            raise HTTPException(status_code=400, detail="Invalid college selection")
        current_user.college_id = updates.college_id

    if updates.custom_college is not None:
        current_user.custom_college = updates.custom_college.strip()

    if updates.department is not None:
        current_user.department = updates.department.strip()

    if updates.year is not None:
        current_user.year = updates.year.strip()

    if updates.preferences is not None:
        current_user.preferences = updates.preferences

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=token, user=UserResponse.model_validate(current_user))


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate a 6-digit OTP and send to email via SMTP.
    Rate-limited: max 3 OTPs per email per hour.
    """
    target_email = body.email.lower().strip()

    # Rate limit: max 3 OTPs per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(minutes=OTP_RESEND_LIMIT_MINUTES)
    recent_count = (
        db.query(OTPCode)
        .filter(OTPCode.email == target_email, OTPCode.created_at >= one_hour_ago)
        .count()
    )
    if recent_count >= OTP_RESEND_LIMIT_COUNT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait an hour before trying again.",
        )

    # Check if user exists
    user = db.query(User).filter(User.email == target_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email.",
        )

    # User exists: generate and save OTP
    otp = _generate_otp()
    
    # Invalidate old OTPs for this email
    db.query(OTPCode).filter(OTPCode.email == target_email, OTPCode.used == False).update({"used": True})

    # Save hashed OTP to database
    otp_record = OTPCode(
        email=target_email,
        code_hash=hash_password(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(otp_record)
    db.commit()

    # Send HTML verification email via SMTP
    background_tasks.add_task(_send_otp_email, target_email, otp, user.full_name, settings)

    res = {
        "message": f"Code sent to {target_email} · expires in 10 minutes",
        "expires_in_minutes": OTP_TTL_MINUTES,
        "email_sent": True,
    }

    if settings.dev_mode:
        res["dev_otp"] = otp
        logger.info("Dev Mode Fallback: SMTP configured or queued. Displaying Dev OTP: %s", otp)

    return res


@router.post("/verify-otp")
def verify_otp(
    body: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP and return a short-lived reset token."""
    target_email = body.email.lower().strip()
    target_otp = body.otp.strip()

    otp_record = (
        db.query(OTPCode)
        .filter(OTPCode.email == target_email, OTPCode.used == False)
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if not otp_record or otp_record.is_expired():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Request a new OTP.")

    if not verify_password(target_otp, otp_record.code_hash):
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(status_code=400, detail=f"Incorrect OTP. {remaining} attempt(s) remaining.")

    # OTP correct — mark as used, return reset token
    otp_record.used = True
    db.commit()

    reset_token = create_access_token(
        data={"sub": target_email, "purpose": "reset_password"},
        expires_delta=timedelta(minutes=15),
    )
    return {"reset_token": reset_token}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the token from verify-otp."""
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(body.reset_token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        purpose = payload.get("purpose")
        if purpose != "reset_password" or not email:
            raise HTTPException(status_code=400, detail="Invalid reset token.")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password reset successfully. Please log in with your new password."}
