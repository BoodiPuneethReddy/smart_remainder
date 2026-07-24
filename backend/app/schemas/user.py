"""schemas/user.py — Pydantic schemas for User and Auth."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    college_id: Optional[int] = None
    college: Optional[str] = None
    custom_college: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    preferences: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    college_id: Optional[int] = None
    custom_college: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    preferences: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

