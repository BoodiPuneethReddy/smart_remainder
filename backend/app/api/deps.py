"""
api/deps.py — FastAPI shared dependencies.
Import get_current_user from here in all protected routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.ai_client import AIInferenceClient, get_ai_client

_bearer = HTTPBearer()

# Singleton AI client — created once at import time
_ai_client_instance: AIInferenceClient | None = None


def get_ai_client_dep() -> AIInferenceClient:
    """Dependency that returns the singleton AI client."""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = get_ai_client()
    return _ai_client_instance


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extract and validate JWT Bearer token.
    Returns the authenticated User or raises 401.
    """
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
