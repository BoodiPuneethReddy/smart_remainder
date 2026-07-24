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
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.otp_code import OTPCode
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

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
    return "".join(random.choices(string.digits, k=6))


def _send_otp_email(email: str, otp: str, full_name: str) -> bool:
    """
    Send a beautifully formatted HTML email containing the reset OTP to the registered email.
    Falls back to a plain-text template for compatible mail clients.

    Returns True if sent successfully, False otherwise.
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    if settings.dev_mode:
        logger.info("DEV MODE — Generated OTP for %s: %s", email, otp)

    if not settings.smtp_host or not settings.smtp_username:
        logger.warning("SMTP not configured — falling back. (host: %r, user: %r)",
                       settings.smtp_host, settings.smtp_username)
        return False

    sender_email = settings.smtp_from_email or settings.smtp_username
    sender_name = settings.smtp_from_name or "Smart Study Reminder AI"

    # Plain text version
    text_content = f"""Smart Study Reminder AI

Hi {full_name},

We received a request to reset your password for your Smart Study Reminder AI account.

Your 6-digit verification code is:

[ {otp} ]

This code is single-use and will expire in {OTP_TTL_MINUTES} minutes. For security, never share this code with anyone.

If you didn't request this change, you can safely ignore this email — your account remains secure.

Smart Study Reminder AI Team — Built for ByteXL × AMD Mini Hackathon
"""

    # High quality professional HTML version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #0b0e14;
      color: #f5f7fa;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}
    .email-container {{
      max-width: 560px;
      margin: 40px auto;
      background-color: #0f1219;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      background: linear-gradient(135deg, #ff6b35 0%, #ffc857 100%);
      padding: 32px 24px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      color: #ffffff;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .content {{
      padding: 40px 32px;
    }}
    .greeting {{
      font-size: 18px;
      font-weight: 600;
      color: #f5f7fa;
      margin-top: 0;
      margin-bottom: 16px;
    }}
    .body-text {{
      font-size: 14px;
      line-height: 1.6;
      color: #98a2b3;
      margin-bottom: 32px;
    }}
    .otp-container {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px dashed rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 24px;
      text-align: center;
      margin-bottom: 32px;
    }}
    .otp-code {{
      font-family: "Courier New", Courier, monospace;
      font-size: 36px;
      font-weight: 700;
      letter-spacing: 6px;
      color: #ff6b35;
      margin: 0;
    }}
    .security-note {{
      font-size: 12px;
      line-height: 1.5;
      color: #ffc857;
      background: rgba(255, 200, 87, 0.08);
      border: 1px solid rgba(255, 200, 87, 0.15);
      padding: 12px 16px;
      border-radius: 6px;
      margin-bottom: 24px;
    }}
    .footer {{
      padding: 24px 32px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      background-color: rgba(255, 255, 255, 0.01);
      text-align: center;
      font-size: 11px;
      color: #98a2b3;
      opacity: 0.8;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1>Smart Study Reminder AI</h1>
    </div>
    <div class="content">
      <p class="greeting">Hi {full_name},</p>
      <p class="body-text">
        We received a request to reset your password for your Smart Study Reminder AI account. Please use the following 6-digit verification code to complete your reset:
      </p>
      <div class="otp-container">
        <p class="otp-code">{otp}</p>
      </div>
      <div class="security-note">
        <strong>Important Security Notice:</strong> This code is single-use, valid for exactly 10 minutes, and must never be shared with anyone.
      </div>
      <p class="body-text" style="margin-bottom: 0;">
        If you didn't request this change, you can safely ignore this email — your account remains secure.
      </p>
    </div>
    <div class="footer">
      Smart Study Reminder AI Team — Built for ByteXL &times; AMD Mini Hackathon
    </div>
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
        logger.error("SMTP delivery failed to %s: %s", email, exc, exc_info=True)
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate a 6-digit OTP and send to email.
    Never reveals whether the email exists (prevents account enumeration).
    Rate-limited: max 3 OTPs per email per hour.
    """
    email = body.email.lower().strip()

    # Rate limit: max 3 OTPs per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(minutes=OTP_RESEND_LIMIT_MINUTES)
    recent_count = (
        db.query(OTPCode)
        .filter(OTPCode.email == email, OTPCode.created_at >= one_hour_ago)
        .count()
    )
    if recent_count >= OTP_RESEND_LIMIT_COUNT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait an hour before trying again.",
        )

    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email. Please create an account first.",
        )

    # User exists: generate and save OTP
    otp = _generate_otp()
    
    # Invalidate old OTPs for this email
    db.query(OTPCode).filter(OTPCode.email == email, OTPCode.used == False).update({"used": True})

    # Save to database
    otp_record = OTPCode(
        email=email,
        code_hash=hash_password(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(otp_record)
    db.commit()

    # Send HTML verification email
    email_sent = _send_otp_email(email, otp, user.full_name)

    # Response preparation
    response = {
        "message": f"Code sent to {email} · expires in 10 minutes",
        "expires_in_minutes": OTP_TTL_MINUTES,
        "email_sent": email_sent,
    }

    # If email succeeded: NEVER return dev_otp, even in dev mode!
    if email_sent:
        return response

    # If email failed:
    if settings.dev_mode:
        response["dev_otp"] = otp
        logger.info("Dev Mode Fallback: SMTP failed or disabled. Displaying Dev OTP: %s", otp)
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification email. Please try again in a moment.",
        )


@router.post("/verify-otp")
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP and return a short-lived reset token."""
    email = body.email.lower().strip()
    otp_record = (
        db.query(OTPCode)
        .filter(OTPCode.email == email, OTPCode.used == False)
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if not otp_record or otp_record.is_expired():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Request a new OTP.")

    if not verify_password(body.otp, otp_record.code_hash):
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(status_code=400, detail=f"Incorrect OTP. {remaining} attempt(s) remaining.")

    # OTP correct — mark as used, return reset token
    otp_record.used = True
    db.commit()

    reset_token = create_access_token(
        data={"sub": email, "purpose": "reset_password"},
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
