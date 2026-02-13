"""
Booking Service - handles appointment booking, rescheduling, and cancellation.
Uses database transactions with row-level locking to prevent double booking.
Google Calendar is updated ONLY after DB transaction succeeds.
"""
from datetime import date, time, datetime, timedelta
import logging
import re
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.config import settings
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.patient_history import PatientHistory
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource
from app.models.calendar_sync_job import CalendarSyncJob
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule
from app.services.availability_service import AvailabilityService
from app.services.calendar_sync_queue import calendar_sync_queue
from app.services.google_calendar_service import GoogleCalendarService
from app.services.rag_sync_service import RAGSyncService
from app.services.notification_service import notification_service
from app.utils.datetime_utils import to_utc, now_ist

logger = logging.getLogger(__name__)


class BookingService:
    """Service for managing appointments."""
    
    def __init__(self):
        self.availability_service = AvailabilityService()
        self.rag_sync_service = RAGSyncService()
    
    def book_appointment(
        self,
        db: Session,
        booking_data: AppointmentCreate
    ) -> Appointment:
        """
        Book a new appointment.
        
        Process:
        1. Validate slot availability from DB
        2. Create or get patient (based on mobile number)
        3. Save patient history if provided
        4. Create appointment in DB with row-level locking
        5. After DB commit, create Google Calendar event
        
        Args:
            db: Database session
            booking_data: Appointment creation data
            
        Returns:
            Created Appointment object
            
        Raises:
            ValueError: If slot not available or validation fails
        """
        # Get doctor first to calculate slot end time
        doctor = db.query(Doctor).filter(Doctor.email == booking_data.doctor_email).first()  # Changed to email
        if not doctor:
            raise ValueError(f"Doctor with email '{booking_data.doctor_email}' not found")

        if not doctor.is_active:
            raise ValueError(f"Doctor with email '{booking_data.doctor_email}' is not active")

        if booking_data.doctor_name:
            def normalize(name: str) -> str:
                name = name.strip().lower()
                name = re.sub(r"^dr\.?\s+", "", name)
                name = re.sub(r"^doctor\s+", "", name)
                name = re.sub(r"\s+", " ", name)
                return name

            requested_name = normalize(booking_data.doctor_name)
            actual_name = normalize(doctor.name)
            if requested_name and actual_name and requested_name not in actual_name and actual_name not in requested_name:
                raise ValueError("Doctor name does not match the selected doctor")

        # Prevent booking in the past (using IST timezone)
        if booking_data.date < now_ist().date():
            raise ValueError("Appointment date cannot be in the past")

        # Calculate slot end time based on doctor's slot duration
        start_datetime = datetime.combine(booking_data.date, booking_data.start_time)
        end_datetime = start_datetime + timedelta(minutes=doctor.slot_duration_minutes)
        slot_end_time = end_datetime.time()

        appointment_tz = settings.DEFAULT_TIMEZONE  # Always IST (Asia/Kolkata) for all doctors
        start_at_utc = to_utc(booking_data.date, booking_data.start_time, appointment_tz)
        end_at_utc = to_utc(booking_data.date, slot_end_time, appointment_tz)

        # Validate slot availability
        if not self.availability_service.is_slot_available(
            db=db,
            doctor_email=booking_data.doctor_email,  # Changed to email
            slot_date=booking_data.date,
            slot_start_time=booking_data.start_time,
            slot_end_time=slot_end_time
        ):
            raise ValueError("Slot is not available")
        
        # Get or create patient based on mobile number
        patient = db.query(Patient).filter(
            Patient.mobile_number == booking_data.patient_mobile_number
        ).first()
        
        if not patient:
            # Create new patient
            patient = Patient(
                name=booking_data.patient_name,
                mobile_number=booking_data.patient_mobile_number,
                email=booking_data.patient_email,
                gender=booking_data.patient_gender,
                date_of_birth=booking_data.patient_date_of_birth
            )
            db.add(patient)
            db.flush()  # Get patient ID
        else:
            # Update existing patient info if provided
            if booking_data.patient_name:
                patient.name = booking_data.patient_name
            if booking_data.patient_email:
                patient.email = booking_data.patient_email
            if booking_data.patient_gender:
                patient.gender = booking_data.patient_gender
            if booking_data.patient_date_of_birth:
                patient.date_of_birth = booking_data.patient_date_of_birth
        
        # Save patient history if provided
        if (booking_data.symptoms or 
            booking_data.medical_conditions or 
            booking_data.allergies or 
            booking_data.notes):
            
            patient_history = PatientHistory(
                patient_id=patient.id,
                symptoms=booking_data.symptoms,
                medical_conditions=booking_data.medical_conditions or [],
                allergies=booking_data.allergies or [],
                notes=booking_data.notes
            )
            db.add(patient_history)
        
        # Create appointment with row-level locking
        # Use SELECT FOR UPDATE to prevent double booking
        try:
            # Check again with lock to prevent race conditions
            existing_appointment = db.query(Appointment).filter(
                Appointment.doctor_email == doctor.email,  # Changed to use doctor.email
                Appointment.date == booking_data.date,
                Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
                Appointment.start_time < slot_end_time,
                Appointment.end_time > booking_data.start_time
            ).with_for_update().first()

            if existing_appointment:
                raise ValueError("Slot has been booked by another request")

            # Create appointment
            appointment = Appointment(
                doctor_email=booking_data.doctor_email,  # Changed to email
                patient_id=patient.id,
                date=booking_data.date,
                start_time=booking_data.start_time,
                end_time=slot_end_time,
                timezone=appointment_tz,
                start_at_utc=start_at_utc,
                end_at_utc=end_at_utc,
                status=AppointmentStatus.BOOKED,
                source=booking_data.source,
                calendar_sync_status="PENDING"
            )
            
            db.add(appointment)
            db.commit()
            db.refresh(appointment)
            
            # Queue calendar sync and run immediately so calendar updates before response
            apt_id_str = str(appointment.id)
            calendar_sync_queue.enqueue_create(apt_id_str)
            calendar_sync_queue.trigger_immediate_sync(apt_id_str, "CREATE")
            db.refresh(appointment)  # Reload to get updated google_calendar_event_id and sync status

            # Send SMS notifications to both doctor and patient (non-blocking)
            try:
                # Doctor SMS notification
                notification_service.send_doctor_booking_sms(
                    doctor_phone=doctor.phone_number,
                    doctor_name=doctor.name,
                    patient_name=patient.name,
                    patient_mobile=patient.mobile_number,
                    appointment_date=appointment.date,
                    appointment_time=appointment.start_time,
                    symptoms=booking_data.symptoms
                )
                # Patient SMS notification (respects sms_opt_in preference)
                notification_service.send_patient_booking_sms(
                    patient_mobile=patient.mobile_number,
                    patient_name=patient.name,
                    doctor_name=doctor.name,
                    doctor_specialization=doctor.specialization,
                    appointment_date=appointment.date,
                    appointment_time=appointment.start_time,
                    clinic_address=doctor.clinic.address if doctor.clinic else settings.CLINIC_ADDRESS,
                    sms_opt_in=patient.sms_opt_in
                )
            except Exception as e:
                logger.warning(f"Failed to send booking notifications: {e}")

            logger.info(f"Successfully booked appointment {appointment.id}")
            return appointment
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during booking: {str(e)}")
            raise ValueError("Failed to book appointment due to database constraint violation")
        except Exception as e:
            db.rollback()
            logger.error(f"Error booking appointment: {str(e)}")
            raise
    
    def reschedule_appointment(
        self,
        db: Session,
        appointment_id: UUID,
        reschedule_data: AppointmentReschedule
    ) -> Appointment:
        """
        Reschedule an existing appointment.
        
        Process:
        1. Get existing appointment
        2. Validate new slot availability
        3. DB transaction:
           - Cancel old appointment
           - Create new appointment
        4. Update Google Calendar event
        
        Args:
            db: Database session
            appointment_id: ID of appointment to reschedule
            reschedule_data: New appointment details
            
        Returns:
            Updated Appointment object
            
        Raises:
            ValueError: If appointment not found or new slot not available
        """
        # Get existing appointment
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        ).first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found or already cancelled")
        
        # Validate new slot availability with lock to avoid race conditions
        if not self.availability_service.is_slot_available(
            db=db,
            doctor_email=appointment.doctor_email,
            slot_date=reschedule_data.new_date,
            slot_start_time=reschedule_data.new_start_time,
            slot_end_time=reschedule_data.new_end_time,
            exclude_appointment_id=appointment.id
        ):
            raise ValueError("New slot is not available")

        overlapping = db.query(Appointment).filter(
            Appointment.doctor_email == appointment.doctor_email,
            Appointment.date == reschedule_data.new_date,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
            Appointment.start_time < reschedule_data.new_end_time,
            Appointment.end_time > reschedule_data.new_start_time,
            Appointment.id != appointment.id
        ).with_for_update().first()
        if overlapping:
            raise ValueError("New slot is not available")

        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.email == appointment.doctor_email).first()  # Changed to email
        if not doctor:
            raise ValueError(f"Doctor with email '{appointment.doctor_email}' not found")
        
        # Get patient
        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
        if not patient:
            raise ValueError(f"Patient {appointment.patient_id} not found")
        
        old_event_id = appointment.google_calendar_event_id
        old_date = appointment.date
        old_start_time = appointment.start_time
        appointment_tz = settings.DEFAULT_TIMEZONE  # Always IST (Asia/Kolkata) for all doctors
        start_at_utc = to_utc(reschedule_data.new_date, reschedule_data.new_start_time, appointment_tz)
        end_at_utc = to_utc(reschedule_data.new_date, reschedule_data.new_end_time, appointment_tz)
        
        try:
            # Update appointment in DB transaction
            appointment.status = AppointmentStatus.RESCHEDULED
            appointment.date = reschedule_data.new_date
            appointment.start_time = reschedule_data.new_start_time
            appointment.end_time = reschedule_data.new_end_time
            appointment.timezone = appointment_tz
            appointment.start_at_utc = start_at_utc
            appointment.end_at_utc = end_at_utc
            appointment.calendar_sync_status = "PENDING"
            
            db.commit()
            db.refresh(appointment)
            
            # Queue calendar sync (for worker retry) then sync immediately in same session
            apt_id_str = str(appointment.id)
            action = "UPDATE" if old_event_id else "CREATE"
            if old_event_id:
                calendar_sync_queue.enqueue_update(apt_id_str)
            else:
                calendar_sync_queue.enqueue_create(apt_id_str)

            cal = GoogleCalendarService()
            if old_event_id:
                result = cal.update_event(
                    doctor_email=appointment.doctor_email,
                    event_id=old_event_id,
                    patient_name=patient.name,
                    appointment_date=appointment.date,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time,
                    description=f"Appointment with {patient.name}",
                    timezone_name=appointment.timezone,
                )
                ok = bool(result)
                # If update_event returned a new event ID (old event was deleted), update DB
                if isinstance(result, str):
                    appointment.google_calendar_event_id = result
            else:
                event_id = cal.create_event(
                    doctor_email=appointment.doctor_email,
                    patient_name=patient.name,
                    appointment_date=appointment.date,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time,
                    description=f"Appointment with {patient.name}",
                    timezone_name=appointment.timezone,
                )
                ok = bool(event_id)
                if ok:
                    appointment.google_calendar_event_id = event_id

            if ok:
                appointment.calendar_sync_status = "SYNCED"
                appointment.calendar_sync_last_error = None
                appointment.calendar_sync_next_attempt_at = None
                job = db.query(CalendarSyncJob).filter(
                    CalendarSyncJob.appointment_id == appointment.id,
                    CalendarSyncJob.action == action,
                    CalendarSyncJob.status.in_(["PENDING", "IN_PROGRESS"]),
                ).first()
                if job:
                    job.status = "COMPLETED"
                db.commit()
                db.refresh(appointment)
            else:
                appointment.calendar_sync_last_error = cal.last_error or "Calendar sync failed"
                db.commit()
                db.refresh(appointment)

            # Send SMS notifications to both doctor and patient (non-blocking)
            try:
                # Doctor SMS notification
                notification_service.send_doctor_reschedule_sms(
                    doctor_phone=doctor.phone_number,
                    doctor_name=doctor.name,
                    patient_name=patient.name,
                    patient_mobile=patient.mobile_number,
                    old_date=old_date,
                    old_time=old_start_time,
                    new_date=reschedule_data.new_date,
                    new_time=reschedule_data.new_start_time
                )
                # Patient SMS notification
                notification_service.send_patient_reschedule_sms(
                    patient_mobile=patient.mobile_number,
                    patient_name=patient.name,
                    doctor_name=doctor.name,
                    doctor_specialization=doctor.specialization,
                    new_date=reschedule_data.new_date,
                    new_time=reschedule_data.new_start_time,
                    clinic_address=doctor.clinic.address if doctor.clinic else settings.CLINIC_ADDRESS,
                    sms_opt_in=patient.sms_opt_in
                )
            except Exception as e:
                logger.warning(f"Failed to send reschedule notifications: {e}")

            logger.info(f"Successfully rescheduled appointment {appointment_id}")
            return appointment

        except Exception as e:
            db.rollback()
            logger.error(f"Error rescheduling appointment: {str(e)}")
            raise
    
    def cancel_appointment(
        self,
        db: Session,
        appointment_id: UUID
    ) -> Appointment:
        """
        Cancel an appointment.
        
        Process:
        1. Mark appointment as cancelled in DB
        2. Delete Google Calendar event
        
        Args:
            db: Database session
            appointment_id: ID of appointment to cancel
            
        Returns:
            Cancelled Appointment object
            
        Raises:
            ValueError: If appointment not found
        """
        # Get appointment
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.email == appointment.doctor_email).first()  # Changed to email
        if not doctor:
            raise ValueError(f"Doctor with email '{appointment.doctor_email}' not found")

        # Get patient for notifications
        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()

        # Store appointment details for notifications before any changes
        appointment_date = appointment.date
        appointment_time = appointment.start_time

        event_id = appointment.google_calendar_event_id

        try:
            # Mark as cancelled in DB (idempotent if already cancelled)
            if appointment.status != AppointmentStatus.CANCELLED:
                appointment.status = AppointmentStatus.CANCELLED
                appointment.calendar_sync_status = "PENDING"
                db.commit()
                db.refresh(appointment)
            
            # Queue calendar sync (for worker retry) then sync immediately in same session
            if event_id:
                calendar_sync_queue.enqueue_delete(str(appointment.id))
                cal = GoogleCalendarService()
                ok = cal.delete_event(doctor_email=appointment.doctor_email, event_id=event_id)
                if ok:
                    appointment.calendar_sync_status = "SYNCED"
                    appointment.calendar_sync_last_error = None
                    appointment.calendar_sync_next_attempt_at = None
                    job = db.query(CalendarSyncJob).filter(
                        CalendarSyncJob.appointment_id == appointment.id,
                        CalendarSyncJob.action == "DELETE",
                        CalendarSyncJob.status.in_(["PENDING", "IN_PROGRESS"]),
                    ).first()
                    if job:
                        job.status = "COMPLETED"
                    db.commit()
                    db.refresh(appointment)
                else:
                    appointment.calendar_sync_last_error = cal.last_error or "Calendar delete failed"
                    db.commit()
                    db.refresh(appointment)
            else:
                # No calendar event to delete
                appointment.calendar_sync_status = "SYNCED"
                db.commit()
                db.refresh(appointment)

            # Send SMS notifications to both doctor and patient (non-blocking)
            if patient:
                try:
                    # Doctor SMS notification
                    notification_service.send_doctor_cancellation_sms(
                        doctor_phone=doctor.phone_number,
                        doctor_name=doctor.name,
                        patient_name=patient.name,
                        patient_mobile=patient.mobile_number,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time
                    )
                    # Patient SMS notification
                    notification_service.send_patient_cancellation_sms(
                        patient_mobile=patient.mobile_number,
                        patient_name=patient.name,
                        doctor_name=doctor.name,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        sms_opt_in=patient.sms_opt_in
                    )
                except Exception as e:
                    logger.warning(f"Failed to send cancellation notifications: {e}")

            logger.info(f"Successfully cancelled appointment {appointment_id}")
            return appointment

        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling appointment: {str(e)}")
            raise
