"""
Common dependencies for the doctor portal.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.doctor_account import DoctorAccount
from app.models.doctor import Doctor
from doctor_portal.security import decode_token

auth_scheme = HTTPBearer(auto_error=False)


def get_portal_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_doctor_account(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_portal_db),
) -> DoctorAccount:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
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
