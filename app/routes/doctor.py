"""
Doctor management API routes.
"""
import threading
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db, SessionLocal
from app.security import verify_api_key
from app.models.doctor import Doctor
from app.models.doctor_leave import DoctorLeave
from app.models.clinic import Clinic
from app.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorListResponse
)
from app.services.rag_sync_service import RAGSyncService
from app.services.calendar_watch_service import calendar_watch_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_sync_service = RAGSyncService()


def _background_rag_sync(doctor_id: str, doctor_data: dict):
    """Run RAG sync in background thread."""
    try:
        # Create a simple object with the needed attributes
        class DoctorProxy:
            pass

        proxy = DoctorProxy()
        for key, value in doctor_data.items():
            setattr(proxy, key, value)

        rag_sync_service.sync_doctor(proxy)
        logger.info(f"Background RAG sync completed for doctor {doctor_data.get('email')}")
    except Exception as e:
        logger.error(f"Background RAG sync failed for doctor {doctor_data.get('email')}: {e}")


def _background_calendar_watch(doctor_email: str):
    """Run calendar watch setup in background thread with its own DB session."""
    try:
        db = SessionLocal()
        try:
            calendar_watch_service.setup_watch_for_doctor(
                doctor_email=doctor_email,
                db=db
            )
            logger.info(f"Background calendar watch setup completed for {doctor_email}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Background calendar watch setup failed for {doctor_email}: {e}")


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    doctor_data: DoctorCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new doctor profile.
    After DB commit, triggers RAG sync with descriptive fields only.
    """
    try:
        # Validate clinic exists
        clinic = db.query(Clinic).filter(Clinic.id == doctor_data.clinic_id).first()
        if not clinic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Clinic with id '{doctor_data.clinic_id}' not found. Please create the clinic first or use a valid clinic ID."
            )

        # Check if email already exists (case-sensitive)
        existing = db.query(Doctor).filter(Doctor.email == doctor_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A doctor with the email address '{doctor_data.email}' already exists. Each doctor must have a unique email address. Please use a different email address."
            )

        # Create doctor
        doctor = Doctor(**doctor_data.model_dump())
        db.add(doctor)
        db.commit()
        db.refresh(doctor)

        # Prepare doctor data for background tasks (avoid detached session issues)
        doctor_dict = {
            "id": str(doctor.id),
            "email": doctor.email,
            "name": doctor.name,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
            "languages": doctor.languages,
            "consultation_type": doctor.consultation_type,
            "phone_number": doctor.phone_number,
        }

        # Trigger RAG sync in background (non-blocking)
        threading.Thread(
            target=_background_rag_sync,
            args=(str(doctor.id), doctor_dict),
            daemon=True,
            name=f"rag-sync-{doctor.email}"
        ).start()
        logger.info(f"Queued background RAG sync for {doctor.email}")

        # Set up Google Calendar watch in background (non-blocking)
        threading.Thread(
            target=_background_calendar_watch,
            args=(doctor.email,),
            daemon=True,
            name=f"calendar-watch-{doctor.email}"
        ).start()
        logger.info(f"Queued background calendar watch for {doctor.email}")

        return doctor
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create doctor: {str(e)}"
        )


@router.get("/{doctor_email}", response_model=DoctorResponse)
async def get_doctor(
    doctor_email: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get doctor by email (unique identifier)."""
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with email '{doctor_email}' not found"
        )
    return doctor


@router.get("/", response_model=DoctorListResponse)
async def list_doctors(
    clinic_id: UUID = None,
    is_active: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List doctors with optional filters."""
    from app.config import settings
    if skip < 0 or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip must be >= 0 and limit must be >= 1"
        )
    if limit > settings.MAX_LIST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"limit must be <= {settings.MAX_LIST_LIMIT}"
        )
    query = db.query(Doctor)
    
    if clinic_id:
        query = query.filter(Doctor.clinic_id == clinic_id)
    if is_active is not None:
        query = query.filter(Doctor.is_active == is_active)
    
    total = query.count()
    doctors = query.offset(skip).limit(limit).all()
    
    return DoctorListResponse(doctors=doctors, total=total)


@router.put("/{doctor_email}", response_model=DoctorResponse)
async def update_doctor(
    doctor_email: str,
    doctor_data: DoctorUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Update doctor profile.
    All updates MUST persist to DB first.
    After DB commit, triggers RAG sync.
    """
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with email '{doctor_email}' not found"
        )
    
    try:
        # Update fields
        update_data = doctor_data.model_dump(exclude_unset=True)
        if "clinic_id" in update_data:
            clinic = db.query(Clinic).filter(Clinic.id == update_data["clinic_id"]).first()
            if not clinic:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Clinic with id '{update_data['clinic_id']}' not found"
                )
        for field, value in update_data.items():
            setattr(doctor, field, value)
        
        db.commit()
        db.refresh(doctor)

        # Prepare doctor data for background task
        doctor_dict = {
            "id": str(doctor.id),
            "email": doctor.email,
            "name": doctor.name,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
            "languages": doctor.languages,
            "consultation_type": doctor.consultation_type,
            "phone_number": doctor.phone_number,
        }

        # Trigger RAG sync in background (non-blocking)
        threading.Thread(
            target=_background_rag_sync,
            args=(str(doctor.id), doctor_dict),
            daemon=True,
            name=f"rag-sync-update-{doctor.email}"
        ).start()

        return doctor

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update doctor: {str(e)}"
        )


@router.post("/{doctor_email}/leaves", status_code=status.HTTP_201_CREATED)
async def add_doctor_leave(
    doctor_email: str,
    leave_date: str,  # ISO date string
    reason: str = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Add a doctor leave/holiday."""
    from datetime import datetime

    doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with email '{doctor_email}' not found"
        )

    try:
        date_obj = datetime.strptime(leave_date, "%Y-%m-%d").date()

        # Check if leave already exists
        existing = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_email == doctor_email,
            DoctorLeave.date == date_obj
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave already exists for date {leave_date}"
            )

        doctor_leave = DoctorLeave(
            doctor_email=doctor_email,
            date=date_obj,
            reason=reason
        )
        
        db.add(doctor_leave)
        db.commit()
        db.refresh(doctor_leave)
        
        return {"message": "Leave added successfully", "leave_id": str(doctor_leave.id)}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding doctor leave: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add leave: {str(e)}"
        )


@router.delete("/{doctor_email}/leaves/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor_leave(
    doctor_email: str,
    leave_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete a doctor leave."""
    doctor_leave = db.query(DoctorLeave).filter(
        DoctorLeave.id == leave_id,
        DoctorLeave.doctor_email == doctor_email
    ).first()
    
    if not doctor_leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave not found"
        )
    
    db.delete(doctor_leave)
    db.commit()
    
    return None


@router.delete("/{doctor_email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    doctor_email: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Hard delete a doctor and all related records."""
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with email '{doctor_email}' not found"
        )

    try:
        db.delete(doctor)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting doctor {doctor_email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete doctor: {str(e)}"
        )
