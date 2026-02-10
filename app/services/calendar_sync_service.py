"""
Calendar Sync Service - syncs changes between Google Calendar and Database.
Handles bidirectional synchronization with conflict resolution.
"""
from datetime import datetime, date, time, timezone
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging

import hashlib
from app.services.google_calendar_service import GoogleCalendarService
from app.services.availability_service import AvailabilityService
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.config import settings
from app.utils.datetime_utils import to_utc, now_ist

logger = logging.getLogger(__name__)


class CalendarSyncService:
    """Service for bidirectional calendar synchronization."""
    
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
        self.availability_service = AvailabilityService()
    
    async def sync_calendar_to_db(
        self,
        doctor_email: str,
        db: Session
    ) -> Dict:
        """
        Sync Google Calendar events to database.
        Called when webhook receives notification.
        
        Strategy:
        1. Fetch all upcoming events from Google Calendar
        2. Compare with database appointments
        3. Identify: new, modified, deleted events
        4. Update database accordingly with conflict resolution
        """
        logger.info(f"Starting calendar sync for {doctor_email}")
        
        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
        if not doctor:
            raise ValueError(f"Doctor with email {doctor_email} not found")
        
        # 1. Fetch events from Google Calendar
        calendar_events = await self._fetch_calendar_events(doctor_email)
        
        # 2. Fetch appointments from database (using IST date)
        db_appointments = db.query(Appointment).filter(
            Appointment.doctor_email == doctor.email,
            Appointment.date >= now_ist().date(),
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        ).all()
        
        # 3. Create lookup maps
        calendar_map = {
            event['id']: event 
            for event in calendar_events 
            if event.get('id')
        }
        
        db_map = {
            apt.google_calendar_event_id: apt 
            for apt in db_appointments 
            if apt.google_calendar_event_id
        }
        
        # 4. Process changes
        stats = {
            'updated': 0,
            'created': 0,
            'deleted': 0,
            'conflicts': 0,
            'skipped': 0
        }
        
        # Find modified events (in both calendar and DB)
        for event_id, calendar_event in calendar_map.items():
            if event_id in db_map:
                # Event exists in both - check if modified
                db_appointment = db_map[event_id]
                if await self._is_event_modified(calendar_event, db_appointment):
                    result = await self._update_appointment_from_calendar(
                        calendar_event,
                        db_appointment,
                        doctor,
                        db
                    )
                    stats[result] += 1
            else:
                # Event in calendar but not in DB - doctor created new event
                result = await self._create_appointment_from_calendar(
                    calendar_event,
                    doctor,
                    db
                )
                stats[result] += 1
        
        # Find deleted events (in DB but not in calendar)
        for event_id, db_appointment in db_map.items():
            if event_id not in calendar_map:
                # Event was deleted from calendar
                result = await self._handle_deleted_event(db_appointment, db)
                stats[result] += 1
        
        db.commit()
        logger.info(f"Calendar sync completed for {doctor_email}: {stats}")
        return stats
    
    async def _fetch_calendar_events(
        self,
        doctor_email: str
    ) -> List[Dict]:
        """Fetch all upcoming events from Google Calendar."""
        try:
            service = self.calendar_service._get_service(doctor_email)
            
            # Fetch events from today onwards
            now = datetime.now(timezone.utc).isoformat()
            
            events_result = self.calendar_service._execute_with_retry(
                lambda: service.events().list(
                    calendarId=doctor_email,
                    timeMin=now,
                    maxResults=100,  # Adjust as needed
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
            )
            
            events = events_result.get('items', [])
            logger.info(f"Fetched {len(events)} events from {doctor_email}")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching calendar events: {str(e)}")
            raise
    
    async def _is_event_modified(
        self,
        calendar_event: Dict,
        db_appointment: Appointment
    ) -> bool:
        """Check if calendar event differs from DB appointment."""
        # Parse calendar event times
        cal_start_str = calendar_event['start'].get('dateTime')
        cal_end_str = calendar_event['end'].get('dateTime')
        
        if not cal_start_str or not cal_end_str:
            return False  # All-day events not supported
        
        cal_start = datetime.fromisoformat(cal_start_str.replace('Z', '+00:00'))
        cal_end = datetime.fromisoformat(cal_end_str.replace('Z', '+00:00'))
        
        # Compare with DB using UTC if available
        if db_appointment.start_at_utc and db_appointment.end_at_utc:
            return (
                cal_start.astimezone(timezone.utc) != db_appointment.start_at_utc or
                cal_end.astimezone(timezone.utc) != db_appointment.end_at_utc
            )

        db_start = datetime.combine(db_appointment.date, db_appointment.start_time)
        db_end = datetime.combine(db_appointment.date, db_appointment.end_time)

        return (
            cal_start.date() != db_start.date() or
            cal_start.time() != db_start.time() or
            cal_end.time() != db_end.time()
        )
    
    async def _update_appointment_from_calendar(
        self,
        calendar_event: Dict,
        db_appointment: Appointment,
        doctor: Doctor,
        db: Session
    ) -> str:
        """Update database appointment with calendar event data."""
        try:
            # Parse new times from calendar
            cal_start_str = calendar_event['start'].get('dateTime')
            cal_end_str = calendar_event['end'].get('dateTime')
            
            cal_start = datetime.fromisoformat(cal_start_str.replace('Z', '+00:00'))
            cal_end = datetime.fromisoformat(cal_end_str.replace('Z', '+00:00'))
            
            new_date = cal_start.date()
            new_start_time = cal_start.time()
            new_end_time = cal_end.time()
            
            # CONFLICT RESOLUTION: Check if new slot is available
            # Temporarily exclude current appointment from availability check
            is_available = self.availability_service.is_slot_available(
                db=db,
                doctor_email=doctor.email,
                slot_date=new_date,
                slot_start_time=new_start_time,
                slot_end_time=new_end_time,
                exclude_appointment_id=db_appointment.id
            )
            
            if not is_available:
                # Conflict detected - new slot overlaps with another appointment
                logger.warning(
                    f"Conflict: Doctor {doctor.email} moved appointment "
                    f"{db_appointment.id} to unavailable slot"
                )
                
                # Strategy: Revert calendar to DB version (recommended)
                await self._revert_calendar_to_db(
                    doctor.email,
                    calendar_event['id'],
                    db_appointment
                )
                
                return 'conflicts'
            
            # Update appointment in database
            appointment_tz = doctor.timezone or settings.DEFAULT_TIMEZONE
            db_appointment.date = new_date
            db_appointment.start_time = new_start_time
            db_appointment.end_time = new_end_time
            db_appointment.timezone = appointment_tz
            db_appointment.start_at_utc = to_utc(new_date, new_start_time, appointment_tz)
            db_appointment.end_at_utc = to_utc(new_date, new_end_time, appointment_tz)
            db_appointment.status = AppointmentStatus.RESCHEDULED
            db_appointment.calendar_sync_status = "SYNCED"
            db_appointment.calendar_sync_last_error = None
            
            logger.info(
                f"Updated appointment {db_appointment.id} from calendar: "
                f"{new_date} {new_start_time}-{new_end_time}"
            )
            
            return 'updated'
            
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}")
            return 'skipped'
    
    async def _create_appointment_from_calendar(
        self,
        calendar_event: Dict,
        doctor: Doctor,
        db: Session
    ) -> str:
        """
        Create new appointment in DB from calendar event.
        This happens when doctor manually creates event in calendar.
        """
        try:
            # Parse event details
            summary = calendar_event.get('summary', 'Manual Booking')
            
            cal_start_str = calendar_event['start'].get('dateTime')
            cal_end_str = calendar_event['end'].get('dateTime')
            
            if not cal_start_str or not cal_end_str:
                return 'skipped'  # All-day events
            
            cal_start = datetime.fromisoformat(cal_start_str.replace('Z', '+00:00'))
            cal_end = datetime.fromisoformat(cal_end_str.replace('Z', '+00:00'))
            
            # Check if slot is available (conflict with AI/admin bookings)
            is_available = self.availability_service.is_slot_available(
                db=db,
                doctor_email=doctor.email,
                slot_date=cal_start.date(),
                slot_start_time=cal_start.time(),
                slot_end_time=cal_end.time()
            )
            
            if not is_available:
                logger.warning(
                    f"Conflict: Doctor {doctor.email} created event that "
                    f"overlaps with existing appointment"
                )
                # Delete the calendar event to prevent confusion
                await self._delete_calendar_event(
                    doctor.email,
                    calendar_event['id']
                )
                return 'conflicts'
            
            # Create "placeholder" appointment for doctor-created events
            # Get or create placeholder patient (use hash to keep under 20 chars)
            email_hash = hashlib.md5(doctor.email.encode()).hexdigest()[:12]
            placeholder_mobile = f"WALKIN-{email_hash}"  # 19 chars max
            placeholder_patient = db.query(Patient).filter(
                Patient.mobile_number == placeholder_mobile
            ).first()
            
            if not placeholder_patient:
                placeholder_patient = Patient(
                    name="Walk-in Patient",
                    mobile_number=placeholder_mobile
                )
                db.add(placeholder_patient)
                db.flush()
            
            # Create appointment
            appointment_tz = doctor.timezone or settings.DEFAULT_TIMEZONE
            appointment = Appointment(
                doctor_email=doctor.email,
                patient_id=placeholder_patient.id,
                date=cal_start.date(),
                start_time=cal_start.time(),
                end_time=cal_end.time(),
                status=AppointmentStatus.BOOKED,
                google_calendar_event_id=calendar_event['id'],
                source=AppointmentSource.ADMIN,  # Doctor created it manually
                timezone=appointment_tz,
                start_at_utc=to_utc(cal_start.date(), cal_start.time(), appointment_tz),
                end_at_utc=to_utc(cal_end.date(), cal_end.time(), appointment_tz)
            )
            appointment.calendar_sync_status = "SYNCED"
            
            db.add(appointment)
            
            logger.info(
                f"Created appointment from calendar event: "
                f"{cal_start.date()} {cal_start.time()}-{cal_end.time()}"
            )
            
            return 'created'
            
        except Exception as e:
            logger.error(f"Error creating appointment from calendar: {str(e)}")
            try:
                db.rollback()
            except Exception:
                pass
            return 'skipped'
    
    async def _handle_deleted_event(
        self,
        db_appointment: Appointment,
        db: Session
    ) -> str:
        """Handle event deleted from calendar."""
        try:
            # Doctor deleted appointment from calendar
            # Mark as cancelled in DB
            db_appointment.status = AppointmentStatus.CANCELLED
            db_appointment.calendar_sync_status = "SYNCED"
            db_appointment.calendar_sync_last_error = None
            
            logger.info(
                f"Marked appointment {db_appointment.id} as cancelled "
                f"(deleted from calendar)"
            )
            
            return 'deleted'
            
        except Exception as e:
            logger.error(f"Error handling deleted event: {str(e)}")
            return 'skipped'
    
    async def _revert_calendar_to_db(
        self,
        doctor_email: str,
        event_id: str,
        db_appointment: Appointment
    ):
        """Revert calendar event to match database (conflict resolution)."""
        try:
            # Update calendar event to match DB
            self.calendar_service.update_event(
                doctor_email=doctor_email,
                event_id=event_id,
                patient_name=db_appointment.patient.name,
                appointment_date=db_appointment.date,
                start_time=db_appointment.start_time,
                end_time=db_appointment.end_time,
                description=f"[REVERTED] Slot conflict detected. Original time restored.",
                timezone_name=db_appointment.timezone
            )
            
            logger.info(f"Reverted calendar event {event_id} to DB version")
            
        except Exception as e:
            logger.error(f"Error reverting calendar event: {str(e)}")
    
    async def _delete_calendar_event(
        self,
        doctor_email: str,
        event_id: str
    ):
        """Delete event from calendar (conflict resolution)."""
        try:
            self.calendar_service.delete_event(doctor_email, event_id)
            logger.info(f"Deleted conflicting calendar event {event_id}")
        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}")
