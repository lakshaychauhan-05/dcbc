"""
Security utilities for the doctor portal.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, status
from jose import JWTError, jwt
import bcrypt

from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash for a password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_portal_access_token(data: Dict[str, Any], expires_minutes: int | None = None) -> str:
    """Create JWT access token for doctor portal."""
    expire_minutes = expires_minutes or settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.DOCTOR_PORTAL_JWT_SECRET,
        algorithm=settings.DOCTOR_PORTAL_JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_portal_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token for doctor portal."""
    try:
        payload = jwt.decode(
            token,
            settings.DOCTOR_PORTAL_JWT_SECRET,
            algorithms=[settings.DOCTOR_PORTAL_JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
