"""
Authentication routes for the doctor portal.
"""
from datetime import datetime, timezone
import secrets
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from doctor_portal.schemas import LoginRequest, RegisterRequest, TokenResponse
from doctor_portal.security import verify_password, create_access_token, get_password_hash
from doctor_portal.dependencies import get_portal_db
from app.models.doctor_account import DoctorAccount
from app.models.doctor import Doctor
from doctor_portal.config import portal_settings
from app.security import verify_api_key

router = APIRouter(prefix="/auth", tags=["Auth"])


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

    token = create_access_token({"sub": account.doctor_email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=portal_settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/oauth/google/start")
def oauth_google_start():
    """
    Initiate Google OAuth flow.
    """
    if not portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID or not portal_settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth not configured",
        )
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
        "redirect_uri": portal_settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
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
            portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
            portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_SECRET,
            portal_settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
            portal_settings.DOCTOR_PORTAL_FRONTEND_CALLBACK_URL,
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
            "client_id": portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
            "client_secret": portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_SECRET,
            "redirect_uri": portal_settings.DOCTOR_PORTAL_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    if token_resp.status_code != 200:
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
            portal_settings.DOCTOR_PORTAL_OAUTH_CLIENT_ID,
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

    portal_token = create_access_token({"sub": account.doctor_email})
    frontend_redirect = f"{portal_settings.DOCTOR_PORTAL_FRONTEND_CALLBACK_URL}?token={portal_token}"
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

    token = create_access_token({"sub": account.doctor_email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=portal_settings.DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
