"""
Authentication routes for the doctor portal.
"""
from datetime import datetime, timezone
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import httpx

from app.portal.schemas import (
    LoginRequest, RegisterRequest, TokenResponse,
    ChangePasswordRequest, MessageResponse
)
from app.portal.security import (
    verify_password, create_portal_access_token, get_password_hash
)
from app.portal.dependencies import get_portal_db, get_current_doctor_account
from app.models.doctor_account import DoctorAccount
from app.models.doctor import Doctor
from app.config import settings
from app.security import verify_api_key

router = APIRouter(tags=["Portal Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_portal_db)) -> TokenResponse:
    """
    Doctor login for the portal.
    """
    account = (
        db.query(DoctorAccount)
        .filter(DoctorAccount.doctor_email == payload.email.lower())
        .first()
    )
    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    doctor = db.query(Doctor).filter(Doctor.email == account.doctor_email, Doctor.is_active == True).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile inactive or missing",
        )

    account.last_login_at = datetime.now(timezone.utc)
    db.add(account)
    db.commit()

    token = create_portal_access_token({"sub": account.doctor_email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/oauth/google/start")
def oauth_google_start():
    """
    Initiate Google OAuth flow.
    """
    if not settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID or not settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth not configured",
        )
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
        "redirect_uri": settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = httpx.URL(base, params=params)
    return {"url": str(url)}


@router.get("/oauth/google/callback")
def oauth_google_callback(code: str, db: Session = Depends(get_portal_db)):
    """
    Handle Google OAuth callback, issue portal token, and redirect to frontend.
    """
    if not all(
        [
            settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
            settings.DOCTOR_PORTAL_OAUTH_CLIENT_SECRET,
            settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
            settings.DOCTOR_PORTAL_FRONTEND_CALLBACK_URL,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth not configured",
        )

    token_resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
            "client_secret": settings.DOCTOR_PORTAL_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    if token_resp.status_code != 200:
        logging.error(f"DEBUG: OAuth Failure Body: {token_resp.text}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth exchange failed",
        )
    token_data = token_resp.json()
    id_token_raw = token_data.get("id_token")
    if not id_token_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing id_token",
        )

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_raw,
            google_requests.Request(),
            settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid id_token",
        )

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not present in id_token",
        )

    doctor = db.query(Doctor).filter(Doctor.email == email.lower(), Doctor.is_active == True).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile inactive or missing",
        )

    account = (
        db.query(DoctorAccount)
        .filter(DoctorAccount.doctor_email == email.lower())
        .first()
    )
    if not account:
        # Auto-provision portal account with random password (unused for OAuth)
        random_password = secrets.token_urlsafe(32)
        account = DoctorAccount(
            doctor_email=email.lower(),
            password_hash=get_password_hash(random_password),
            is_active=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    account.last_login_at = datetime.now(timezone.utc)
    db.add(account)
    db.commit()

    portal_token = create_portal_access_token({"sub": account.doctor_email})
    frontend_redirect = f"{settings.DOCTOR_PORTAL_FRONTEND_CALLBACK_URL}?token={portal_token}"
    return RedirectResponse(url=frontend_redirect, status_code=status.HTTP_302_FOUND)


@router.post(
    "/register",
    response_model=TokenResponse,
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Session = Depends(get_portal_db)) -> TokenResponse:
    """
    Provision a doctor portal account.
    Protected by the existing X-API-Key used across services.
    """
    doctor = db.query(Doctor).filter(Doctor.email == payload.email.lower()).first()
    if not doctor or not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or inactive",
        )

    existing = (
        db.query(DoctorAccount)
        .filter(DoctorAccount.doctor_email == payload.email.lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists for this doctor",
        )

    account = DoctorAccount(
        doctor_email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        is_active=True,
    )
    db.add(account)
    db.commit()

    token = create_portal_access_token({"sub": account.doctor_email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> MessageResponse:
    """
    Change doctor portal password.
    """
    if not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    account.password_hash = get_password_hash(payload.new_password)
    account.updated_at = datetime.now(timezone.utc)
    db.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/logout", response_model=MessageResponse)
def logout(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> MessageResponse:
    """
    Logout the current doctor.
    Note: JWT tokens are stateless. This endpoint logs the logout event
    and client should discard the token.
    """
    logging.info(f"Doctor {account.doctor_email} logged out")
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> TokenResponse:
    """
    Refresh the access token.
    The current valid token is used to issue a new token with extended expiry.
    """
    # Verify doctor is still active
    doctor = db.query(Doctor).filter(
        Doctor.email == account.doctor_email,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile inactive or missing",
        )

    # Issue new token
    new_token = create_portal_access_token({"sub": account.doctor_email})
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in_minutes=settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
