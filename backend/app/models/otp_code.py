"""models/otp_code.py — OTP for password reset"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)   # bcrypt hashed OTP
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        expires = self.expires_at
        if expires.tzinfo is not None:
            return datetime.now(timezone.utc) > expires
        return datetime.utcnow() > expires

    def __repr__(self) -> str:
        return f"<OTPCode email={self.email!r} used={self.used} expires={self.expires_at}>"
