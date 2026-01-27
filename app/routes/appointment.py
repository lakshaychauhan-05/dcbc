"""
Appointment management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
import json

from app.database import get_db
from app.security import verify_api_key
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentResponse,
    AvailabilityResponse
)
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
availability_service = AvailabilityService()
booking_service = BookingService()


@router.get("/availability/{doctor_email}", response_model=AvailabilityResponse)
async def get_availability(
    doctor_email: str,
    date: date,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get available slots for a doctor on a specific date.
    Database is the single source of truth for availability.
    """
    try:
        availability = availability_service.get_available_slots(
            db=db,
            doctor_email=doctor_email,
            target_date=date
        )
        return availability
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get availability: {str(e)}"
        )


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Book a new appointment.
    
    Process:
    1. Validate slot availability from DB
    2. Create patient if not exists (based on mobile number)
    3. Save patient symptoms and medical history
    4. Use DB transaction + row-level locking to prevent double booking
    5. After DB commit, create Google Calendar event
    """
    try:
        appointment = booking_service.book_appointment(
            db=db,
            booking_data=appointment_data
        )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to book appointment: {str(e)}"
        )


@router.get("/availability-search")
async def search_availability(
    specialization: Optional[str] = None,
    language: Optional[str] = None,
    date: Optional[date] = None,
    clinic_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Advanced availability search for chatbot.
    Find doctors by specialization, language, and check availability.
    """
    try:
        # Build doctor query based on filters
        query = db.query(Doctor).filter(Doctor.is_active == True)

        if clinic_id:
            query = query.filter(Doctor.clinic_id == clinic_id)
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        if language:
            query = query.filter(Doctor.languages.any(language))

        doctors = query.all()

        # Get availability for each doctor if date is specified
        results = []
        for doctor in doctors:
            doctor_info = {
                "email": doctor.email,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "experience_years": doctor.experience_years,
                "languages": doctor.languages,
                "working_days": doctor.working_days,
                "working_hours": doctor.working_hours,
                "slot_duration_minutes": doctor.slot_duration_minutes
            }

            if date:
                try:
                    availability = availability_service.get_available_slots(
                        db=db,
                        doctor_email=doctor.email,
                        target_date=date
                    )
                    doctor_info["available_slots"] = availability.available_slots
                    doctor_info["is_available"] = len(availability.available_slots) > 0
                except Exception as e:
                    logger.warning(f"Could not get availability for {doctor.email}: {str(e)}")
                    doctor_info["available_slots"] = []
                    doctor_info["is_available"] = False
            else:
                doctor_info["available_slots"] = None
                doctor_info["is_available"] = None

            results.append(doctor_info)

        return {
            "doctors": results,
            "search_criteria": {
                "specialization": specialization,
                "language": language,
                "date": date.isoformat() if date else None,
                "clinic_id": str(clinic_id) if clinic_id else None
            },
            "total_results": len(results)
        }

    except Exception as e:
        logger.error(f"Error searching availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search availability: {str(e)}"
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get appointment by ID."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    return appointment


@router.get("/doctor/{doctor_email}", response_model=List[AppointmentResponse])
async def get_doctor_appointments(
    doctor_email: str,
    start_date: date = None,
    end_date: date = None,
    status_filter: AppointmentStatus = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get appointments for a doctor with optional filters."""
    query = db.query(Appointment).filter(Appointment.doctor_email == doctor_email)
    
    if start_date:
        query = query.filter(Appointment.date >= start_date)
    if end_date:
        query = query.filter(Appointment.date <= end_date)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    
    appointments = query.order_by(Appointment.date, Appointment.start_time).offset(skip).limit(limit).all()
    return appointments


@router.get("/patient/{patient_id}", response_model=List[AppointmentResponse])
async def get_patient_appointments(
    patient_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get appointments for a patient."""
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.date.desc(), Appointment.start_time.desc()).offset(skip).limit(limit).all()
    
    return appointments


@router.put("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: UUID,
    reschedule_data: AppointmentReschedule,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Reschedule an appointment.
    
    Process:
    1. DB transaction: Cancel old slot, book new slot
    2. Update Google Calendar event accordingly
    """
    try:
        appointment = booking_service.reschedule_appointment(
            db=db,
            appointment_id=appointment_id,
            reschedule_data=reschedule_data
        )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule appointment: {str(e)}"
        )


@router.delete("/{appointment_id}", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Cancel an appointment.

    Process:
    1. Mark appointment cancelled in DB
    2. Delete or update Google Calendar event
    """
    try:
        appointment = booking_service.cancel_appointment(
            db=db,
            appointment_id=appointment_id
        )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel appointment: {str(e)}"
        )


# Enhanced endpoints for chatbot integration

@router.get("/doctors/export")
async def export_doctors_data(
    clinic_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Export doctor data for chatbot consumption.
    Returns enriched JSON data about doctors for LLM context.
    """
    try:
        query = db.query(Doctor).filter(Doctor.is_active == True)

        if clinic_id:
            query = query.filter(Doctor.clinic_id == clinic_id)

        doctors = query.all()

        # Convert to chatbot-friendly format
        doctors_data = []
        for doctor in doctors:
            doctor_dict = {
                "email": doctor.email,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "experience_years": doctor.experience_years,
                "languages": doctor.languages,
                "consultation_type": doctor.consultation_type,
                "working_days": doctor.working_days,
                "working_hours": doctor.working_hours,
                "slot_duration_minutes": doctor.slot_duration_minutes,
                "general_working_days_text": doctor.general_working_days_text,
                "clinic_id": str(doctor.clinic_id)
            }
            doctors_data.append(doctor_dict)

        return {
            "doctors": doctors_data,
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_doctors": len(doctors_data)
        }

    except Exception as e:
        logger.error(f"Error exporting doctor data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export doctor data: {str(e)}"
        )


@router.post("/webhook/appointment-changed")
async def appointment_change_webhook(
    appointment_data: dict,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Webhook endpoint for chatbot to receive appointment change notifications.
    Called when appointments are created, updated, or cancelled.
    """
    try:
        # This webhook can be used by chatbot to update its knowledge
        # For now, just log the notification
        logger.info(f"Appointment change webhook received: {appointment_data}")

        # In production, this could trigger chatbot notifications to users
        # about appointment changes, reminders, etc.

        return {"status": "received", "message": "Appointment change notification processed"}

    except Exception as e:
        logger.error(f"Error processing appointment webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )
