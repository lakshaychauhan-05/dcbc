"""
Admin-facing management routes with direct database access.
Replaces the old HTTP proxy approach now that all services are unified.
"""
import logging
import secrets
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from app.admin.dependencies import get_current_admin
from app.database import get_db
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.doctor_account import DoctorAccount
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.portal.security import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Management"], dependencies=[Depends(get_current_admin)])


# ============== SCHEMAS ==============

class ClinicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: bool = True


class ClinicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class ClinicResponse(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DoctorCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    clinic_id: UUID
    specialization: str = "General"
    experience_years: int = 0
    languages: List[str] = Field(default_factory=lambda: ["English"])
    consultation_type: str = "in_person"
    timezone: str = "Asia/Kolkata"
    phone_number: Optional[str] = None
    google_calendar_id: Optional[str] = None
    slot_duration_minutes: int = 30
    is_active: bool = True
    initial_password: Optional[str] = None  # For portal account creation


class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    clinic_id: Optional[UUID] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    languages: Optional[List[str]] = None
    consultation_type: Optional[str] = None
    timezone: Optional[str] = None
    phone_number: Optional[str] = None
    google_calendar_id: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class DoctorResponse(BaseModel):
    email: str
    name: str
    clinic_id: str
    clinic_name: Optional[str] = None
    specialization: str
    experience_years: int
    languages: List[str]
    consultation_type: str
    timezone: str
    phone_number: Optional[str] = None
    google_calendar_id: Optional[str] = None
    slot_duration_minutes: int
    is_active: bool
    has_portal_account: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    portal_account_created: Optional[bool] = None
    portal_login_ready: Optional[bool] = None

    class Config:
        from_attributes = True


class PortalAccountResponse(BaseModel):
    password: str
    portal_response: Dict[str, Any]


# ============== CLINIC ROUTES ==============

@router.get("/clinics", response_model=List[ClinicResponse])
def list_clinics(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all clinics with optional filtering."""
    query = db.query(Clinic)
    if is_active is not None:
        query = query.filter(Clinic.is_active == is_active)
    clinics = query.offset(skip).limit(limit).all()
    return [
        ClinicResponse(
            id=str(c.id),
            name=c.name,
            address=c.address,
            phone_number=getattr(c, 'phone_number', None),
            email=getattr(c, 'email', None),
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in clinics
    ]


@router.get("/clinics/{clinic_id}", response_model=ClinicResponse)
def get_clinic(clinic_id: UUID, db: Session = Depends(get_db)):
    """Get a single clinic by ID."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        address=clinic.address,
        phone_number=getattr(clinic, 'phone_number', None),
        email=getattr(clinic, 'email', None),
        is_active=clinic.is_active,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )


@router.post("/clinics", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
def create_clinic(payload: ClinicCreate, db: Session = Depends(get_db)):
    """Create a new clinic."""
    clinic = Clinic(
        name=payload.name,
        address=payload.address,
        is_active=payload.is_active,
    )
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        address=clinic.address,
        phone_number=getattr(clinic, 'phone_number', None),
        email=getattr(clinic, 'email', None),
        is_active=clinic.is_active,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )


@router.put("/clinics/{clinic_id}", response_model=ClinicResponse)
def update_clinic(clinic_id: UUID, payload: ClinicUpdate, db: Session = Depends(get_db)):
    """Update a clinic."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    if payload.name is not None:
        clinic.name = payload.name
    if payload.address is not None:
        clinic.address = payload.address
    # phone_number and email fields are optional - only update if model supports them
    if payload.phone_number is not None and hasattr(clinic, 'phone_number'):
        clinic.phone_number = payload.phone_number
    if payload.email is not None and hasattr(clinic, 'email'):
        clinic.email = payload.email
    if payload.is_active is not None:
        clinic.is_active = payload.is_active

    clinic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clinic)

    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        address=clinic.address,
        phone_number=getattr(clinic, 'phone_number', None),
        email=getattr(clinic, 'email', None),
        is_active=clinic.is_active,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )


@router.delete("/clinics/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clinic(clinic_id: UUID, force: bool = False, db: Session = Depends(get_db)):
    """Delete a clinic. Use force=True to delete even with associated doctors."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    # Check for associated doctors
    doctors = db.query(Doctor).filter(Doctor.clinic_id == clinic_id).count()
    if doctors > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clinic has {doctors} associated doctors. Use force=true to delete anyway.",
        )

    db.delete(clinic)
    db.commit()
    return None


# ============== DOCTOR ROUTES ==============

@router.get("/doctors", response_model=List[DoctorResponse])
def list_doctors(
    clinic_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all doctors with optional filtering."""
    query = db.query(Doctor)
    if clinic_id is not None:
        query = query.filter(Doctor.clinic_id == clinic_id)
    if is_active is not None:
        query = query.filter(Doctor.is_active == is_active)
    doctors = query.offset(skip).limit(limit).all()

    # Get all doctor emails that have portal accounts
    doctor_emails = [d.email for d in doctors]
    portal_accounts = db.query(DoctorAccount.doctor_email).filter(
        DoctorAccount.doctor_email.in_(doctor_emails)
    ).all()
    portal_emails = {a.doctor_email for a in portal_accounts}

    return [
        DoctorResponse(
            email=d.email,
            name=d.name,
            clinic_id=str(d.clinic_id),
            clinic_name=d.clinic.name if d.clinic else None,
            specialization=d.specialization,
            experience_years=d.experience_years,
            languages=d.languages,
            consultation_type=d.consultation_type,
            timezone=d.timezone,
            phone_number=d.phone_number,
            google_calendar_id=getattr(d, 'google_calendar_id', d.email),
            slot_duration_minutes=d.slot_duration_minutes,
            is_active=d.is_active,
            has_portal_account=d.email in portal_emails,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in doctors
    ]


@router.get("/doctors/{doctor_email}", response_model=DoctorResponse)
def get_doctor(doctor_email: str, db: Session = Depends(get_db)):
    """Get a single doctor by email."""
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email.lower()).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Check if portal account exists
    has_portal = db.query(DoctorAccount).filter(
        DoctorAccount.doctor_email == doctor_email.lower()
    ).first() is not None

    return DoctorResponse(
        email=doctor.email,
        name=doctor.name,
        clinic_id=str(doctor.clinic_id),
        clinic_name=doctor.clinic.name if doctor.clinic else None,
        specialization=doctor.specialization,
        experience_years=doctor.experience_years,
        languages=doctor.languages,
        consultation_type=doctor.consultation_type,
        timezone=doctor.timezone,
        phone_number=doctor.phone_number,
        google_calendar_id=getattr(doctor, 'google_calendar_id', doctor.email),
        slot_duration_minutes=doctor.slot_duration_minutes,
        is_active=doctor.is_active,
        has_portal_account=has_portal,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at,
    )


@router.post("/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db)):
    """
    Create a new doctor.
    Also automatically creates a portal login account if initial_password is provided.
    """
    # Check if clinic exists
    clinic = db.query(Clinic).filter(Clinic.id == payload.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    # Check if doctor already exists
    existing = db.query(Doctor).filter(Doctor.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor with this email already exists",
        )

    # Build doctor data - only include fields that exist in the model
    doctor_data = {
        "email": payload.email.lower(),
        "name": payload.name,
        "clinic_id": payload.clinic_id,
        "specialization": payload.specialization,
        "experience_years": payload.experience_years,
        "languages": payload.languages,
        "consultation_type": payload.consultation_type,
        "timezone": payload.timezone,
        "phone_number": payload.phone_number,
        "slot_duration_minutes": payload.slot_duration_minutes,
        "is_active": payload.is_active,
        "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "working_hours": {"start": "09:00", "end": "17:00"},
    }
    # Only add google_calendar_id if the Doctor model supports it
    if hasattr(Doctor, 'google_calendar_id'):
        doctor_data["google_calendar_id"] = payload.google_calendar_id or payload.email.lower()

    doctor = Doctor(**doctor_data)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    portal_account_created = False
    portal_login_ready = False

    # If initial_password provided, create portal account
    if payload.initial_password:
        try:
            existing_account = (
                db.query(DoctorAccount)
                .filter(DoctorAccount.doctor_email == payload.email.lower())
                .first()
            )
            if not existing_account:
                account = DoctorAccount(
                    doctor_email=payload.email.lower(),
                    password_hash=get_password_hash(payload.initial_password),
                    is_active=True,
                )
                db.add(account)
                db.commit()
                portal_account_created = True
                portal_login_ready = True
        except Exception as e:
            logger.warning(f"Failed to create portal account for {payload.email}: {e}")

    return DoctorResponse(
        email=doctor.email,
        name=doctor.name,
        clinic_id=str(doctor.clinic_id),
        clinic_name=doctor.clinic.name if doctor.clinic else None,
        specialization=doctor.specialization,
        experience_years=doctor.experience_years,
        languages=doctor.languages,
        consultation_type=doctor.consultation_type,
        timezone=doctor.timezone,
        phone_number=doctor.phone_number,
        google_calendar_id=getattr(doctor, 'google_calendar_id', doctor.email),
        slot_duration_minutes=doctor.slot_duration_minutes,
        is_active=doctor.is_active,
        has_portal_account=portal_account_created,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at,
        portal_account_created=portal_account_created,
        portal_login_ready=portal_login_ready,
    )


@router.put("/doctors/{doctor_email}", response_model=DoctorResponse)
def update_doctor(doctor_email: str, payload: DoctorUpdate, db: Session = Depends(get_db)):
    """Update a doctor."""
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email.lower()).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    if payload.name is not None:
        doctor.name = payload.name
    if payload.clinic_id is not None:
        # Verify clinic exists
        clinic = db.query(Clinic).filter(Clinic.id == payload.clinic_id).first()
        if not clinic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
        doctor.clinic_id = payload.clinic_id
    if payload.specialization is not None:
        doctor.specialization = payload.specialization
    if payload.experience_years is not None:
        doctor.experience_years = payload.experience_years
    if payload.languages is not None:
        doctor.languages = payload.languages
    if payload.consultation_type is not None:
        doctor.consultation_type = payload.consultation_type
    if payload.timezone is not None:
        doctor.timezone = payload.timezone
    if payload.phone_number is not None:
        doctor.phone_number = payload.phone_number
    if payload.google_calendar_id is not None and hasattr(doctor, 'google_calendar_id'):
        doctor.google_calendar_id = payload.google_calendar_id
    if payload.slot_duration_minutes is not None:
        doctor.slot_duration_minutes = payload.slot_duration_minutes
    if payload.is_active is not None:
        doctor.is_active = payload.is_active

    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doctor)

    # Check if portal account exists
    has_portal = db.query(DoctorAccount).filter(
        DoctorAccount.doctor_email == doctor_email.lower()
    ).first() is not None

    return DoctorResponse(
        email=doctor.email,
        name=doctor.name,
        clinic_id=str(doctor.clinic_id),
        clinic_name=doctor.clinic.name if doctor.clinic else None,
        specialization=doctor.specialization,
        experience_years=doctor.experience_years,
        languages=doctor.languages,
        consultation_type=doctor.consultation_type,
        timezone=doctor.timezone,
        phone_number=doctor.phone_number,
        google_calendar_id=getattr(doctor, 'google_calendar_id', doctor.email),
        slot_duration_minutes=doctor.slot_duration_minutes,
        is_active=doctor.is_active,
        has_portal_account=has_portal,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at,
    )


@router.delete("/doctors/{doctor_email}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(doctor_email: str, db: Session = Depends(get_db)):
    """Delete a doctor (soft delete - sets is_active to False)."""
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email.lower()).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Soft delete
    doctor.is_active = False
    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()
    return None


@router.post("/doctors/{doctor_email}/portal-account", response_model=PortalAccountResponse, status_code=status.HTTP_201_CREATED)
def provision_portal_account(doctor_email: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Provision a doctor portal account.
    If password not provided, generate a secure random one and return it to the caller.
    """
    # Verify doctor exists
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email.lower()).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Check if account already exists
    existing = (
        db.query(DoctorAccount)
        .filter(DoctorAccount.doctor_email == doctor_email.lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portal account already exists for this doctor",
        )

    generated = password or secrets.token_urlsafe(14)
    account = DoctorAccount(
        doctor_email=doctor_email.lower(),
        password_hash=get_password_hash(generated),
        is_active=True,
    )
    db.add(account)
    db.commit()

    return PortalAccountResponse(
        password=generated,
        portal_response={"status": "created", "email": doctor_email.lower()},
    )


# ============== PATIENT ROUTES (Read-only for admin) ==============

@router.get("/patients")
def list_patients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all patients (read-only for admin)."""
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "mobile_number": p.mobile_number,
            "email": p.email,
            "gender": p.gender,
            "date_of_birth": str(p.date_of_birth) if p.date_of_birth else None,
            "sms_opt_in": p.sms_opt_in,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in patients
    ]


# ============== STATISTICS ==============

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get overall system statistics."""
    return {
        "clinics": db.query(Clinic).filter(Clinic.is_active == True).count(),
        "doctors": db.query(Doctor).filter(Doctor.is_active == True).count(),
        "patients": db.query(Patient).count(),
        "appointments": db.query(Appointment).count(),
    }
