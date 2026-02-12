"""
Common dependencies for the doctor portal.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.models.doctor_account import DoctorAccount
from app.models.doctor import Doctor
from app.portal.security import decode_portal_token

portal_auth_scheme = HTTPBearer(auto_error=False)


def get_portal_db():
    """Get database session for portal routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_doctor_account(
    credentials: HTTPAuthorizationCredentials = Depends(portal_auth_scheme),
    db: Session = Depends(get_portal_db),
) -> DoctorAccount:
    """Verify JWT token and return the current doctor account."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_portal_token(credentials.credentials)
    doctor_email: str | None = payload.get("sub")
    if not doctor_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    account = (
        db.query(DoctorAccount)
        .filter(DoctorAccount.doctor_email == doctor_email)
        .first()
    )
    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account inactive or not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    doctor = db.query(Doctor).filter(Doctor.email == doctor_email, Doctor.is_active == True).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile not found or inactive",
        )

    # Attach doctor instance for downstream use
    account.doctor = doctor
    return account
