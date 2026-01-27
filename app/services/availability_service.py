"""
Availability Service - calculates available slots from database.
Database is the single source of truth for availability.
"""
from datetime import date, time, datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor_leave import DoctorLeave
from app.schemas.appointment import AvailabilitySlot, AvailabilityResponse
import calendar


class AvailabilityService:
    """Service for calculating doctor availability."""
    
    @staticmethod
    def get_available_slots(
        db: Session,
        doctor_email: str,
        target_date: date
    ) -> AvailabilityResponse:
        """
        Calculate available slots for a doctor on a specific date.

        Logic:
        1. Get doctor working hours and slot duration from DB
        2. Generate all possible slots based on working hours
        3. Exclude booked appointments (status=BOOKED)
        4. Exclude doctor leaves
        5. Return available slots

        Args:
            db: Database session
            doctor_email: Email of the doctor (unique identifier)
            target_date: Date to check availability

        Returns:
            AvailabilityResponse with available slots

        Raises:
            ValueError: If doctor not found or inactive
        """
        # Get doctor from DB
        doctor = db.query(Doctor).filter(
            Doctor.email == doctor_email,
            Doctor.is_active == True
        ).first()
        
        if not doctor:
            raise ValueError(f"Doctor with email '{doctor_email}' not found or inactive")

        # Check if doctor works on this day
        day_name = target_date.strftime("%A").lower()
        if day_name not in [day.lower() for day in doctor.working_days]:
            return AvailabilityResponse(
                doctor_id=doctor_email,  # Changed to email
                date=target_date,
                available_slots=[],
                total_slots=0
            )

        # Check if doctor is on leave
        leave = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_email == doctor_email,  # Changed to email
            DoctorLeave.date == target_date
        ).first()

        if leave:
            return AvailabilityResponse(
                doctor_id=doctor_email,  # Changed to email
                date=target_date,
                available_slots=[],
                total_slots=0
            )
        
        # Get working hours
        working_start = datetime.strptime(doctor.working_hours["start"], "%H:%M").time()
        working_end = datetime.strptime(doctor.working_hours["end"], "%H:%M").time()
        
        # Generate all possible slots
        all_slots = AvailabilityService._generate_slots(
            working_start,
            working_end,
            doctor.slot_duration_minutes
        )
        
        # Get booked appointments for this date
        booked_appointments = db.query(Appointment).filter(
            Appointment.doctor_email == doctor_email,  # Changed to email
            Appointment.date == target_date,
            Appointment.status == AppointmentStatus.BOOKED
        ).all()
        
        # Create set of booked time ranges for quick lookup
        booked_ranges = set()
        for apt in booked_appointments:
            booked_ranges.add((apt.start_time, apt.end_time))
        
        # Filter out booked slots
        available_slots = []
        for slot in all_slots:
            is_booked = False
            for booked_start, booked_end in booked_ranges:
                # Check if slot overlaps with booked appointment
                if not (slot.end_time <= booked_start or slot.start_time >= booked_end):
                    is_booked = True
                    break
            
            if not is_booked:
                available_slots.append(slot)
        
        return AvailabilityResponse(
            doctor_id=doctor_email,  # Changed to email
            date=target_date,
            available_slots=available_slots,
            total_slots=len(available_slots)
        )
    
    @staticmethod
    def _generate_slots(
        start_time: time,
        end_time: time,
        slot_duration_minutes: int
    ) -> List[AvailabilitySlot]:
        """
        Generate all possible time slots between start and end time.
        
        Args:
            start_time: Start time of working hours
            end_time: End time of working hours
            slot_duration_minutes: Duration of each slot in minutes
            
        Returns:
            List of AvailabilitySlot objects
        """
        slots = []
        
        # Convert times to datetime for easier calculation
        start_datetime = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        
        current = start_datetime
        slot_duration = timedelta(minutes=slot_duration_minutes)
        
        while current + slot_duration <= end_datetime:
            slot_start = current.time()
            slot_end = (current + slot_duration).time()
            
            slots.append(AvailabilitySlot(
                start_time=slot_start,
                end_time=slot_end
            ))
            
            current += slot_duration
        
        return slots
    
    @staticmethod
    def is_slot_available(
        db: Session,
        doctor_email: str,  # Changed to email
        slot_date: date,
        slot_start_time: time,
        slot_end_time: time
    ) -> bool:
        """
        Check if a specific slot is available.
        Used for booking validation.

        Args:
            db: Database session
            doctor_email: Email of the doctor (unique identifier)
            slot_date: Date of the slot
            slot_start_time: Start time of the slot
            slot_end_time: End time of the slot

        Returns:
            True if slot is available, False otherwise
        """
        # Check if doctor exists and is active
        doctor = db.query(Doctor).filter(
            Doctor.email == doctor_email,  # Changed to email
            Doctor.is_active == True
        ).first()

        if not doctor:
            return False
        
        # Check if doctor works on this day
        day_name = slot_date.strftime("%A").lower()
        if day_name not in [day.lower() for day in doctor.working_days]:
            return False
        
        # Check if doctor is on leave
        leave = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_email == doctor_email,  # Changed to email
            DoctorLeave.date == slot_date
        ).first()
        
        if leave:
            return False
        
        # Check if slot is within working hours
        working_start = datetime.strptime(doctor.working_hours["start"], "%H:%M").time()
        working_end = datetime.strptime(doctor.working_hours["end"], "%H:%M").time()
        
        if slot_start_time < working_start or slot_end_time > working_end:
            return False
        
        # Check if slot duration matches
        slot_duration = (
            datetime.combine(date.today(), slot_end_time) -
            datetime.combine(date.today(), slot_start_time)
        ).total_seconds() / 60
        
        if slot_duration != doctor.slot_duration_minutes:
            return False
        
        # Check for overlapping appointments
        overlapping = db.query(Appointment).filter(
            Appointment.doctor_email == doctor_email,  # Changed to email
            Appointment.date == slot_date,
            Appointment.status == AppointmentStatus.BOOKED,
            or_(
                and_(
                    Appointment.start_time < slot_end_time,
                    Appointment.end_time > slot_start_time
                )
            )
        ).first()
        
        return overlapping is None
