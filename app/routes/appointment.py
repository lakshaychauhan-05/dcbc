"""
Appointment management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timezone, timedelta

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
from app.config import settings
from app.services.booking_service import BookingService
from app.services.idempotency_service import IdempotencyService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
availability_service = AvailabilityService()
booking_service = BookingService()
idempotency_service = IdempotencyService()
_doctor_export_cache = {"timestamp": None, "clinic_id": None, "data": None}


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
        today = datetime.now(timezone.utc).date()
        max_date = today + timedelta(days=settings.MAX_AVAILABILITY_DAYS)
        if date < today or date > max_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"date must be between today and {max_date.isoformat()}"
            )

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
    api_key: str = Depends(verify_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
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
    record = None
    try:
        if idempotency_key:
            payload_json = appointment_data.model_dump(mode="json")
            record, existing = idempotency_service.begin(
                db=db,
                key=idempotency_key,
                endpoint="POST:/api/v1/appointments",
                payload=payload_json
            )
            if existing:
                existing_result = idempotency_service.validate_existing(existing, payload_json)
                if existing_result["status"] == "conflict":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key reuse with different payload"
                    )
                if existing_result["status"] == "completed":
                    return JSONResponse(
                        status_code=existing_result["response_status"],
                        content=existing_result["response"]
                    )
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content={"status": "processing"}
                )

        appointment = booking_service.book_appointment(
            db=db,
            booking_data=appointment_data
        )
        # Serialize appointment for response
        appointment_model = AppointmentResponse.model_validate(appointment)
        
        # For idempotency storage, use JSON-serializable format
        if idempotency_key:
            import json
            # model_dump_json() returns JSON string with dates serialized
            json_str = appointment_model.model_dump_json()
            response_payload = json.loads(json_str)  # Parse back to dict with strings
            idempotency_service.complete(db, record, response_payload, status.HTTP_201_CREATED)
            
        return appointment_model
    except ValueError as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": str(e)},
                status.HTTP_400_BAD_REQUEST
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": f"Failed to book appointment: {str(e)}"},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        logger.error(f"Error booking appointment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to book appointment: {str(e)}"
        )


@router.get("/availability-search")
async def search_availability(
    specialization: Optional[str] = None,
    language: Optional[str] = None,
    target_date: Optional[date] = Query(default=None, alias="date"),
    clinic_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Advanced availability search for chatbot.
    Find doctors by specialization, language, and check availability.
    """
    try:
        if skip < 0 or limit < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="skip must be >= 0 and limit must be >= 1"
            )
        if limit > settings.MAX_AVAILABILITY_RESULTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"limit must be <= {settings.MAX_AVAILABILITY_RESULTS}"
            )

        if target_date:
            today = datetime.now(timezone.utc).date()
            max_date = today + timedelta(days=settings.MAX_AVAILABILITY_DAYS)
            if target_date < today or target_date > max_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"date must be between today and {max_date.isoformat()}"
                )

        if specialization and len(specialization) > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization too long")
        if language and len(language) > 50:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="language too long")

        # Build doctor query based on filters
        query = db.query(Doctor).filter(Doctor.is_active == True)

        if clinic_id:
            query = query.filter(Doctor.clinic_id == clinic_id)
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        if language:
            query = query.filter(Doctor.languages.any(language))

        total = query.count()
        doctors = query.offset(skip).limit(limit).all()

        availability_map = {}
        if target_date:
            availability_map = availability_service.get_available_slots_for_doctors(
                db=db,
                doctors=doctors,
                target_date=target_date
            )

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
                "slot_duration_minutes": doctor.slot_duration_minutes,
                "timezone": doctor.timezone
            }

            if target_date:
                try:
                    availability = availability_map.get(doctor.email)
                    if availability is None:
                        availability = availability_service.get_available_slots(
                            db=db,
                            doctor_email=doctor.email,
                            target_date=target_date
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
                "date": target_date.isoformat() if target_date else None,
                "clinic_id": str(clinic_id) if clinic_id else None,
                "skip": skip,
                "limit": limit
            },
            "total_results": total
        }

    except Exception as e:
        logger.error(f"Error searching availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search availability: {str(e)}"
        )


@router.get("/availability/search")
async def search_availability_alias(
    specialization: Optional[str] = None,
    language: Optional[str] = None,
    target_date: Optional[date] = Query(default=None, alias="date"),
    clinic_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Backward-compatible alias for availability search."""
    return await search_availability(
        specialization=specialization,
        language=language,
        target_date=target_date,
        clinic_id=clinic_id,
        skip=skip,
        limit=limit,
        db=db,
        api_key=api_key
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
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.date.desc(), Appointment.start_time.desc()).offset(skip).limit(limit).all()
    
    return appointments


@router.put("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: UUID,
    reschedule_data: AppointmentReschedule,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
):
    """
    Reschedule an appointment.
    
    Process:
    1. DB transaction: Cancel old slot, book new slot
    2. Update Google Calendar event accordingly
    """
    record = None
    try:
        if idempotency_key:
            payload_json = reschedule_data.model_dump(mode="json")
            record, existing = idempotency_service.begin(
                db=db,
                key=idempotency_key,
                endpoint=f"PUT:/api/v1/appointments/{appointment_id}/reschedule",
                payload=payload_json
            )
            if existing:
                existing_result = idempotency_service.validate_existing(existing, payload_json)
                if existing_result["status"] == "conflict":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key reuse with different payload"
                    )
                if existing_result["status"] == "completed":
                    return JSONResponse(
                        status_code=existing_result["response_status"],
                        content=existing_result["response"]
                    )
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content={"status": "processing"}
                )

        appointment = booking_service.reschedule_appointment(
            db=db,
            appointment_id=appointment_id,
            reschedule_data=reschedule_data
        )
        appointment_model = AppointmentResponse.model_validate(appointment)
        
        if idempotency_key:
            import json
            json_str = appointment_model.model_dump_json()
            response_payload = json.loads(json_str)
            idempotency_service.complete(db, record, response_payload, status.HTTP_200_OK)
            
        return appointment_model
    except ValueError as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": str(e)},
                status.HTTP_400_BAD_REQUEST
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": f"Failed to reschedule appointment: {str(e)}"},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        logger.error(f"Error rescheduling appointment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule appointment: {str(e)}"
        )


@router.delete("/{appointment_id}", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
):
    """
    Cancel an appointment.

    Process:
    1. Mark appointment cancelled in DB
    2. Delete or update Google Calendar event
    """
    record = None
    try:
        if idempotency_key:
            record, existing = idempotency_service.begin(
                db=db,
                key=idempotency_key,
                endpoint=f"DELETE:/api/v1/appointments/{appointment_id}",
                payload={"appointment_id": str(appointment_id)}
            )
            if existing:
                existing_result = idempotency_service.validate_existing(existing, {"appointment_id": str(appointment_id)})
                if existing_result["status"] == "conflict":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key reuse with different payload"
                    )
                if existing_result["status"] == "completed":
                    return JSONResponse(
                        status_code=existing_result["response_status"],
                        content=existing_result["response"]
                    )
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content={"status": "processing"}
                )

        appointment = booking_service.cancel_appointment(
            db=db,
            appointment_id=appointment_id
        )
        appointment_model = AppointmentResponse.model_validate(appointment)
        
        if idempotency_key:
            import json
            json_str = appointment_model.model_dump_json()
            response_payload = json.loads(json_str)
            idempotency_service.complete(db, record, response_payload, status.HTTP_200_OK)
            
        return appointment_model
    except ValueError as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": str(e)},
                status.HTTP_400_BAD_REQUEST
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        if record:
            idempotency_service.complete(
                db,
                record,
                {"detail": f"Failed to cancel appointment: {str(e)}"},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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
        now = datetime.now(timezone.utc)
        cache_ts = _doctor_export_cache.get("timestamp")
        cache_clinic = _doctor_export_cache.get("clinic_id")
        if (
            cache_ts
            and (now - cache_ts).total_seconds() <= settings.DOCTOR_EXPORT_CACHE_TTL_SECONDS
            and cache_clinic == (str(clinic_id) if clinic_id else None)
            and _doctor_export_cache.get("data")
        ):
            return _doctor_export_cache["data"]

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
                "clinic_id": str(doctor.clinic_id),
                "timezone": doctor.timezone
            }
            doctors_data.append(doctor_dict)

        response_payload = {
            "doctors": doctors_data,
            "export_timestamp": now.isoformat(),
            "total_doctors": len(doctors_data)
        }
        _doctor_export_cache["timestamp"] = now
        _doctor_export_cache["clinic_id"] = str(clinic_id) if clinic_id else None
        _doctor_export_cache["data"] = response_payload

        return response_payload

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
