"""
Admin authentication routes.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from admin_portal.config import admin_settings
from admin_portal.security import verify_password, get_password_hash, create_access_token


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


router = APIRouter(prefix="/auth", tags=["AdminAuth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: AdminLoginRequest) -> TokenResponse:
    """
    Single-admin login using env-provided credentials.
    """
    if payload.email.lower() != admin_settings.ADMIN_EMAIL.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stored_hash = admin_settings.ADMIN_PASSWORD_HASH
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PASSWORD_HASH not configured; set a bcrypt hash for the admin user",
        )

    if not verify_password(payload.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": admin_settings.ADMIN_EMAIL})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=admin_settings.ADMIN_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
