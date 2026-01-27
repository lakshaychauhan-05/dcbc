"""
Doctor management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.security import verify_api_key
from app.models.doctor import Doctor
from app.models.doctor_leave import DoctorLeave
from app.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorListResponse
)
from app.services.rag_sync_service import RAGSyncService
from app.services.calendar_watch_service import CalendarWatchService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_sync_service = RAGSyncService()
calendar_watch_service = CalendarWatchService()


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
        
        # Trigger RAG sync after DB commit
        try:
            rag_sync_service.sync_doctor(doctor)
        except Exception as e:
            logger.error(f"Failed to sync doctor to RAG: {str(e)}")
            # Don't fail the request if RAG sync fails
        
        # Set up Google Calendar watch for two-way sync
        try:
            calendar_watch_service.setup_watch_for_doctor(
                doctor_email=doctor.email,
                db=db
            )
            logger.info(f"Successfully set up calendar watch for {doctor.email}")
            logger.info(f"Successfully set up calendar watch for {doctor.email}")
        except Exception as e:
            logger.error(f"Failed to set up calendar watch: {str(e)}")
            # Don't fail doctor creation if watch setup fails
        
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
        for field, value in update_data.items():
            setattr(doctor, field, value)
        
        db.commit()
        db.refresh(doctor)
        
        # Trigger RAG sync after DB commit
        try:
            rag_sync_service.sync_doctor(doctor)
        except Exception as e:
            logger.error(f"Failed to sync doctor to RAG: {str(e)}")
        
        return doctor
        
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
