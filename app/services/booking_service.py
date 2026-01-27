"""
Booking Service - handles appointment booking, rescheduling, and cancellation.
Uses database transactions with row-level locking to prevent double booking.
Google Calendar is updated ONLY after DB transaction succeeds.
"""
from datetime import date, time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
import logging

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.patient_history import PatientHistory
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule
from app.services.availability_service import AvailabilityService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.rag_sync_service import RAGSyncService

logger = logging.getLogger(__name__)


class BookingService:
    """Service for managing appointments."""
    
    def __init__(self):
        self.availability_service = AvailabilityService()
        self.google_calendar_service = GoogleCalendarService()
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

        # Calculate slot end time based on doctor's slot duration
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(booking_data.date, booking_data.start_time)
        end_datetime = start_datetime + timedelta(minutes=doctor.slot_duration_minutes)
        slot_end_time = end_datetime.time()

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
                Appointment.status == AppointmentStatus.BOOKED,
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
                status=AppointmentStatus.BOOKED,
                source=booking_data.source
            )
            
            db.add(appointment)
            db.commit()
            db.refresh(appointment)
            
            # After DB commit, create Google Calendar event
            try:
                event_id = self.google_calendar_service.create_event(
                    doctor_email=doctor.email,
                    patient_name=patient.name,
                    appointment_date=appointment.date,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time,
                    description=f"Appointment with {patient.name}"
                )
                
                if event_id:
                    appointment.google_calendar_event_id = event_id
                    db.commit()
                    db.refresh(appointment)
            except Exception as e:
                # Log but don't fail - Google Calendar is just a mirror
                logger.error(f"Failed to create Google Calendar event: {str(e)}")
            
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
            Appointment.status == AppointmentStatus.BOOKED
        ).first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found or already cancelled")
        
        # Validate new slot availability
        if not self.availability_service.is_slot_available(
            db=db,
            doctor_email=appointment.doctor_email,  # Changed to use appointment.doctor_email
            slot_date=reschedule_data.new_date,
            slot_start_time=reschedule_data.new_start_time,
            slot_end_time=reschedule_data.new_end_time
        ):
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
        
        try:
            # Update appointment in DB transaction
            appointment.status = AppointmentStatus.RESCHEDULED
            appointment.date = reschedule_data.new_date
            appointment.start_time = reschedule_data.new_start_time
            appointment.end_time = reschedule_data.new_end_time
            
            db.commit()
            db.refresh(appointment)
            
            # Update Google Calendar event
            if old_event_id:
                try:
                    self.google_calendar_service.update_event(
                        doctor_email=doctor.email,
                        event_id=old_event_id,
                        patient_name=patient.name,
                        appointment_date=reschedule_data.new_date,
                        start_time=reschedule_data.new_start_time,
                        end_time=reschedule_data.new_end_time
                    )
                except Exception as e:
                    logger.error(f"Failed to update Google Calendar event: {str(e)}")
            
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
            Appointment.id == appointment_id,
            Appointment.status == AppointmentStatus.BOOKED
        ).first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found or already cancelled")
        
        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.email == appointment.doctor_email).first()  # Changed to email
        if not doctor:
            raise ValueError(f"Doctor with email '{appointment.doctor_email}' not found")
        
        event_id = appointment.google_calendar_event_id
        
        try:
            # Mark as cancelled in DB
            appointment.status = AppointmentStatus.CANCELLED
            
            db.commit()
            db.refresh(appointment)
            
            # Delete Google Calendar event
            if event_id:
                try:
                    self.google_calendar_service.delete_event(
                        doctor_email=doctor.email,
                        event_id=event_id
                    )
                except Exception as e:
                    logger.error(f"Failed to delete Google Calendar event: {str(e)}")
            
            logger.info(f"Successfully cancelled appointment {appointment_id}")
            return appointment
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling appointment: {str(e)}")
            raise
