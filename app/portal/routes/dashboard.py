"""
Dashboard and data access routes for the doctor portal.
"""
import logging
import threading
from datetime import date, datetime, timezone
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, noload

from app.portal.dependencies import get_current_doctor_account, get_portal_db
from app.portal.schemas import (
    DoctorProfile,
    AppointmentItem,
    AppointmentsResponse,
    PatientSummary,
    PatientsResponse,
    PatientDetail,
    PatientHistoryItem,
    OverviewResponse,
    RescheduleRequest,
    CancelRequest,
    CompleteRequest,
    AddPatientHistoryRequest,
    UpdatePatientHistoryRequest,
    UpdatePatientRequest,
    UpdateProfileRequest,
    MessageResponse,
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.patient_history import PatientHistory
from app.models.doctor import Doctor
from app.services.calendar_sync_queue import calendar_sync_queue
from app.services.notification_service import notification_service
from app.services.google_calendar_service import GoogleCalendarService
from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portal Dashboard"])


@router.get("/me", response_model=DoctorProfile)
def get_me(account=Depends(get_current_doctor_account)) -> DoctorProfile:
    doctor = account.doctor
    return DoctorProfile.model_validate(doctor)


def _appointment_to_item(appt: Appointment, patient: Patient) -> AppointmentItem:
    return AppointmentItem(
        id=str(appt.id),
        date=appt.date,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        timezone=appt.timezone,
        patient=PatientSummary(
            id=str(patient.id),
            name=patient.name,
            mobile_number=patient.mobile_number,
            email=patient.email,
            sms_opt_in=patient.sms_opt_in,
        ),
        notes=appt.notes,
        source=appt.source.value if appt.source else None,
        calendar_sync_status=appt.calendar_sync_status,
        created_at=appt.created_at,
    )


@router.get("/appointments", response_model=AppointmentsResponse)
def list_appointments(
    start_date: date | None = None,
    end_date: date | None = None,
    status_filter: AppointmentStatus | None = None,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> AppointmentsResponse:
    query = (
        db.query(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(Appointment.doctor_email == account.doctor_email)
    )

    if start_date:
        query = query.filter(Appointment.date >= start_date)
    if end_date:
        query = query.filter(Appointment.date <= end_date)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    rows = query.order_by(Appointment.date, Appointment.start_time).all()
    items = [_appointment_to_item(appt, patient) for appt, patient in rows]
    return AppointmentsResponse(appointments=items)


@router.get("/patients", response_model=PatientsResponse)
def list_patients(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientsResponse:
    patients = (
        db.query(Patient)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .filter(Appointment.doctor_email == account.doctor_email)
        .distinct(Patient.id)
        .all()
    )
    summaries = [
        PatientSummary(
            id=str(p.id),
            name=p.name,
            mobile_number=p.mobile_number,
            email=p.email,
            sms_opt_in=p.sms_opt_in,
        )
        for p in patients
    ]
    return PatientsResponse(patients=summaries)


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient_detail(
    patient_id: UUID,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientDetail:
    # Ensure the doctor has at least one appointment with this patient
    has_access = (
        db.query(Appointment.id)
        .filter(Appointment.doctor_email == account.doctor_email, Appointment.patient_id == patient_id)
        .first()
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found for this doctor",
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    history = (
        db.query(PatientHistory)
        .filter(PatientHistory.patient_id == patient_id)
        .order_by(PatientHistory.created_at.desc())
        .all()
    )

    history_items = [
        PatientHistoryItem.model_validate(item) for item in history
    ]

    return PatientDetail(
        id=str(patient.id),
        name=patient.name,
        mobile_number=patient.mobile_number,
        email=patient.email,
        gender=patient.gender,
        date_of_birth=patient.date_of_birth,
        history=history_items,
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> OverviewResponse:
    today = datetime.now(timezone.utc).date()
    upcoming_query = (
        db.query(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(
            Appointment.doctor_email == account.doctor_email,
            Appointment.date >= today,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
        )
        .order_by(Appointment.date, Appointment.start_time)
        .limit(20)
    )
    rows = upcoming_query.all()
    upcoming = [_appointment_to_item(appt, patient) for appt, patient in rows]

    doctor_profile = DoctorProfile.model_validate(account.doctor)
    return OverviewResponse(doctor=doctor_profile, upcoming_appointments=upcoming)


# ============== APPOINTMENT MANAGEMENT ==============

def _get_appointment_for_doctor(
    appointment_id: UUID,
    db: Session,
    doctor_email: str,
) -> Appointment:
    """Helper to get appointment and verify doctor access."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if appointment.doctor_email != doctor_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this appointment",
        )
    return appointment


@router.post("/appointments/{appointment_id}/cancel", response_model=MessageResponse)
def cancel_appointment(
    appointment_id: UUID,
    payload: CancelRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> MessageResponse:
    """Cancel an appointment with calendar sync and notifications."""
    appointment = _get_appointment_for_doctor(appointment_id, db, account.doctor_email)

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled",
        )
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed appointment",
        )

    # Get doctor and patient for notifications
    doctor = db.query(Doctor).filter(Doctor.email == account.doctor_email).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()

    # Store values for background thread (avoid using ORM objects after session closes)
    doctor_email = account.doctor_email
    doctor_phone = doctor.phone_number if doctor else None
    doctor_name = doctor.name if doctor else "Doctor"
    patient_name = patient.name if patient else "Patient"
    patient_mobile = patient.mobile_number if patient else None
    patient_sms_opt_in = patient.sms_opt_in if patient else True
    appointment_date = appointment.date
    appointment_time = appointment.start_time
    event_id = appointment.google_calendar_event_id

    # Update appointment status
    appointment.status = AppointmentStatus.CANCELLED
    appointment.calendar_sync_status = "PENDING"
    if payload.reason:
        appointment.notes = f"Cancelled by doctor: {payload.reason}"

    db.commit()
    db.refresh(appointment)

    # Sync calendar delete in background (always sync for direct portal actions)
    # Check if Google Calendar is configured (credentials path and admin email)
    calendar_configured = bool(
        settings.GOOGLE_CALENDAR_CREDENTIALS_PATH and
        settings.GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL
    )

    if calendar_configured and event_id:
        def _sync_calendar_delete():
            bg_db = SessionLocal()
            try:
                calendar_sync_queue.enqueue_delete(str(appointment_id))
                cal = GoogleCalendarService()
                ok = cal.delete_event(doctor_email=doctor_email, event_id=event_id)

                # Update sync status in database
                appt = bg_db.query(Appointment).options(noload('*')).filter(Appointment.id == appointment_id).first()
                if appt:
                    if ok:
                        appt.calendar_sync_status = "SYNCED"
                        appt.calendar_sync_last_error = None
                        appt.google_calendar_event_id = None  # Clear event ID after deletion
                        logger.info(f"Calendar delete synced for appointment {appointment_id}")
                    else:
                        appt.calendar_sync_status = "FAILED"
                        appt.calendar_sync_last_error = cal.last_error or "Calendar delete failed"
                        logger.warning(f"Calendar delete failed for appointment {appointment_id}: {cal.last_error}")
                    bg_db.commit()
            except Exception as e:
                logger.error(f"Failed to sync calendar delete: {e}")
                try:
                    appt = bg_db.query(Appointment).options(noload('*')).filter(Appointment.id == appointment_id).first()
                    if appt:
                        appt.calendar_sync_status = "FAILED"
                        appt.calendar_sync_last_error = str(e)[:500]
                        bg_db.commit()
                except Exception:
                    pass
            finally:
                bg_db.close()

        threading.Thread(target=_sync_calendar_delete, daemon=True).start()
    elif not event_id:
        # No calendar event exists - nothing to delete, mark as synced
        appointment.calendar_sync_status = "SYNCED"
        appointment.calendar_sync_last_error = None
        db.commit()
        logger.info(f"No calendar event to delete for appointment {appointment_id}, marked as SYNCED")
    elif not calendar_configured:
        logger.debug(f"Google Calendar not configured, skipping calendar sync for cancelled appointment {appointment_id}")

    # Send notifications in background using captured variables (not ORM objects)
    def _send_notifications():
        try:
            if patient_mobile:
                # Doctor SMS
                notification_service.send_doctor_cancellation_sms(
                    doctor_phone=doctor_phone,
                    doctor_name=doctor_name,
                    patient_name=patient_name,
                    patient_mobile=patient_mobile,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time
                )
                # Patient SMS
                notification_service.send_patient_cancellation_sms(
                    patient_mobile=patient_mobile,
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    sms_opt_in=patient_sms_opt_in
                )
        except Exception as e:
            logger.warning(f"Failed to send cancellation notifications: {e}")

    threading.Thread(target=_send_notifications, daemon=True).start()

    return MessageResponse(message="Appointment cancelled successfully")


@router.post("/appointments/{appointment_id}/complete", response_model=MessageResponse)
def complete_appointment(
    appointment_id: UUID,
    payload: CompleteRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> MessageResponse:
    """Mark an appointment as completed."""
    appointment = _get_appointment_for_doctor(appointment_id, db, account.doctor_email)

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled appointment",
        )
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already completed",
        )

    # Validate appointment is not in the future (cannot complete future appointments)
    appointment_datetime = datetime.combine(appointment.date, appointment.start_time)
    # Make it timezone-aware using UTC
    appointment_datetime_utc = appointment_datetime.replace(tzinfo=timezone.utc)
    if appointment_datetime_utc > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete future appointments. Wait until the appointment time has passed.",
        )

    appointment.status = AppointmentStatus.COMPLETED
    appointment.updated_at = datetime.now(timezone.utc)
    if payload.notes:
        appointment.notes = payload.notes

    db.commit()
    return MessageResponse(message="Appointment marked as completed")


@router.put("/appointments/{appointment_id}/reschedule", response_model=MessageResponse)
def reschedule_appointment(
    appointment_id: UUID,
    payload: RescheduleRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> MessageResponse:
    """Reschedule an appointment with calendar sync and notifications."""
    from app.utils.datetime_utils import to_utc

    appointment = _get_appointment_for_doctor(appointment_id, db, account.doctor_email)

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reschedule a cancelled appointment",
        )
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reschedule a completed appointment",
        )

    # Check for conflicts with existing appointments
    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_email == account.doctor_email,
            Appointment.date == payload.new_date,
            Appointment.id != appointment_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
            # Check for time overlap
            Appointment.start_time < payload.new_end_time,
            Appointment.end_time > payload.new_start_time,
        )
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot conflicts with another appointment",
        )

    # Get doctor and patient for notifications
    doctor = db.query(Doctor).filter(Doctor.email == account.doctor_email).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()

    # Store values for background thread (avoid using ORM objects after session closes)
    doctor_email = account.doctor_email
    doctor_phone = doctor.phone_number if doctor else None
    doctor_name = doctor.name if doctor else "Doctor"
    doctor_specialization = doctor.specialization if doctor else "General"
    clinic_address = doctor.clinic.address if doctor and doctor.clinic else settings.CLINIC_ADDRESS
    patient_name = patient.name if patient else "Patient"
    patient_mobile = patient.mobile_number if patient else None
    patient_sms_opt_in = patient.sms_opt_in if patient else True

    # Store old appointment details for notifications
    old_date = appointment.date
    old_time = appointment.start_time
    old_event_id = appointment.google_calendar_event_id

    # Calculate UTC times
    appointment_tz = doctor.timezone if doctor else settings.DEFAULT_TIMEZONE
    start_at_utc = to_utc(payload.new_date, payload.new_start_time, appointment_tz)
    end_at_utc = to_utc(payload.new_date, payload.new_end_time, appointment_tz)

    # Update appointment
    appointment.date = payload.new_date
    appointment.start_time = payload.new_start_time
    appointment.end_time = payload.new_end_time
    appointment.start_at_utc = start_at_utc
    appointment.end_at_utc = end_at_utc
    appointment.timezone = appointment_tz
    appointment.status = AppointmentStatus.RESCHEDULED
    appointment.calendar_sync_status = "PENDING"
    if payload.reason:
        appointment.notes = f"Rescheduled: {payload.reason}"

    db.commit()
    db.refresh(appointment)

    # Sync calendar in background (always sync for direct portal actions)
    # Check if Google Calendar is configured
    calendar_configured = bool(
        settings.GOOGLE_CALENDAR_CREDENTIALS_PATH and
        settings.GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL
    )

    if calendar_configured:
        def _sync_calendar():
            bg_db = SessionLocal()
            try:
                cal = GoogleCalendarService()
                ok = False
                new_event_id = None

                if old_event_id:
                    calendar_sync_queue.enqueue_update(str(appointment_id))
                    result = cal.update_event(
                        doctor_email=doctor_email,
                        event_id=old_event_id,
                        patient_name=patient_name,
                        appointment_date=payload.new_date,
                        start_time=payload.new_start_time,
                        end_time=payload.new_end_time,
                        description=f"Appointment with {patient_name}",
                        timezone_name=appointment_tz,
                    )
                    ok = bool(result)
                    if isinstance(result, str):
                        new_event_id = result
                    logger.info(f"Calendar update synced for appointment {appointment_id}")
                else:
                    calendar_sync_queue.enqueue_create(str(appointment_id))
                    new_event_id = cal.create_event(
                        doctor_email=doctor_email,
                        patient_name=patient_name,
                        appointment_date=payload.new_date,
                        start_time=payload.new_start_time,
                        end_time=payload.new_end_time,
                        description=f"Appointment with {patient_name}",
                        timezone_name=appointment_tz,
                    )
                    ok = bool(new_event_id)
                    logger.info(f"Calendar create synced for appointment {appointment_id}")

                # Update sync status in database
                appt = bg_db.query(Appointment).options(noload('*')).filter(Appointment.id == appointment_id).first()
                if appt:
                    if ok:
                        appt.calendar_sync_status = "SYNCED"
                        appt.calendar_sync_last_error = None
                        if new_event_id:
                            appt.google_calendar_event_id = new_event_id
                    else:
                        appt.calendar_sync_status = "FAILED"
                        appt.calendar_sync_last_error = cal.last_error or "Calendar sync failed"
                        logger.warning(f"Calendar sync failed for appointment {appointment_id}: {cal.last_error}")
                    bg_db.commit()
            except Exception as e:
                logger.error(f"Failed to sync calendar for reschedule: {e}")
                try:
                    appt = bg_db.query(Appointment).options(noload('*')).filter(Appointment.id == appointment_id).first()
                    if appt:
                        appt.calendar_sync_status = "FAILED"
                        appt.calendar_sync_last_error = str(e)[:500]
                        bg_db.commit()
                except Exception:
                    pass
            finally:
                bg_db.close()

        threading.Thread(target=_sync_calendar, daemon=True).start()
    else:
        logger.debug(f"Google Calendar not configured, skipping calendar sync for rescheduled appointment {appointment_id}")

    # Send notifications in background using captured variables (not ORM objects)
    def _send_notifications():
        try:
            if patient_mobile:
                # Doctor SMS
                notification_service.send_doctor_reschedule_sms(
                    doctor_phone=doctor_phone,
                    doctor_name=doctor_name,
                    patient_name=patient_name,
                    patient_mobile=patient_mobile,
                    old_date=old_date,
                    old_time=old_time,
                    new_date=payload.new_date,
                    new_time=payload.new_start_time
                )
                # Patient SMS
                notification_service.send_patient_reschedule_sms(
                    patient_mobile=patient_mobile,
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    doctor_specialization=doctor_specialization,
                    new_date=payload.new_date,
                    new_time=payload.new_start_time,
                    clinic_address=clinic_address,
                    sms_opt_in=patient_sms_opt_in
                )
        except Exception as e:
            logger.warning(f"Failed to send reschedule notifications: {e}")

    threading.Thread(target=_send_notifications, daemon=True).start()

    return MessageResponse(message="Appointment rescheduled successfully")


# ============== PATIENT MANAGEMENT ==============

def _get_patient_for_doctor(
    patient_id: UUID,
    db: Session,
    doctor_email: str,
) -> Patient:
    """Helper to get patient and verify doctor access."""
    has_access = (
        db.query(Appointment.id)
        .filter(Appointment.doctor_email == doctor_email, Appointment.patient_id == patient_id)
        .first()
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found for this doctor",
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return patient


@router.post("/patients/{patient_id}/history", response_model=PatientHistoryItem)
def add_patient_history(
    patient_id: UUID,
    payload: AddPatientHistoryRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientHistoryItem:
    """Add a new medical history entry for a patient."""
    patient = _get_patient_for_doctor(patient_id, db, account.doctor_email)

    history_entry = PatientHistory(
        id=uuid.uuid4(),
        patient_id=patient.id,
        symptoms=payload.symptoms,
        medical_conditions=payload.medical_conditions or [],
        allergies=payload.allergies or [],
        notes=payload.notes,
        created_at=datetime.now(timezone.utc),
    )

    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    return PatientHistoryItem.model_validate(history_entry)


@router.put("/patients/{patient_id}/history/{history_id}", response_model=PatientHistoryItem)
def update_patient_history(
    patient_id: UUID,
    history_id: UUID,
    payload: UpdatePatientHistoryRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientHistoryItem:
    """Update an existing medical history entry."""
    _get_patient_for_doctor(patient_id, db, account.doctor_email)

    history_entry = (
        db.query(PatientHistory)
        .filter(PatientHistory.id == history_id, PatientHistory.patient_id == patient_id)
        .first()
    )
    if not history_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )

    if payload.symptoms is not None:
        history_entry.symptoms = payload.symptoms
    if payload.medical_conditions is not None:
        history_entry.medical_conditions = payload.medical_conditions
    if payload.allergies is not None:
        history_entry.allergies = payload.allergies
    if payload.notes is not None:
        history_entry.notes = payload.notes

    db.commit()
    db.refresh(history_entry)

    return PatientHistoryItem.model_validate(history_entry)


@router.put("/patients/{patient_id}", response_model=PatientSummary)
def update_patient(
    patient_id: UUID,
    payload: UpdatePatientRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientSummary:
    """Update patient information."""
    patient = _get_patient_for_doctor(patient_id, db, account.doctor_email)

    if payload.name is not None:
        patient.name = payload.name
    if payload.mobile_number is not None:
        patient.mobile_number = payload.mobile_number
    if payload.email is not None:
        patient.email = payload.email
    if payload.gender is not None:
        patient.gender = payload.gender
    if payload.date_of_birth is not None:
        patient.date_of_birth = payload.date_of_birth

    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)

    return PatientSummary(
        id=str(patient.id),
        name=patient.name,
        mobile_number=patient.mobile_number,
        email=patient.email,
        sms_opt_in=patient.sms_opt_in,
    )


# ============== PROFILE MANAGEMENT ==============

@router.put("/me", response_model=DoctorProfile)
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> DoctorProfile:
    """Update doctor profile."""
    doctor = db.query(Doctor).filter(Doctor.email == account.doctor_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    if payload.name is not None:
        doctor.name = payload.name
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

    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doctor)

    return DoctorProfile.model_validate(doctor)
