"""
Google Calendar Service - syncs appointments with Google Calendar.
Google Calendar is ONLY a mirror of confirmed appointments.
Never reads availability from Google Calendar.
"""
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, date, time, timezone
from typing import Optional
from app.config import settings
import logging
import time as time_module
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Project root for resolving relative paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def _resolve_credentials_path(path: str) -> str:
    """Resolve credentials path to absolute path."""
    if not path:
        return path
    # Already absolute
    if os.path.isabs(path):
        return path
    # Handle ./ prefix
    if path.startswith("./"):
        path = path[2:]
    # Resolve relative to project root
    abs_path = str(_PROJECT_ROOT / path)
    return abs_path


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self):
        """Initialize Google Calendar service with service account credentials."""
        # Always resolve to absolute path to avoid working directory issues
        self.credentials_path = _resolve_credentials_path(settings.GOOGLE_CALENDAR_CREDENTIALS_PATH)
        self.delegated_admin_email = settings.GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL
        self._service = None
        self.last_error: Optional[str] = None  # Stores detailed error from last failed operation
    
    def _get_service(self, user_email: str):
        """
        Get Google Calendar service for a specific user (doctor).
        
        Args:
            user_email: Doctor's Google Calendar email
            
        Returns:
            Google Calendar service instance
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            if self._should_delegate(user_email):
                delegated_credentials = credentials.with_subject(user_email)
                logger.info(f"Using domain-wide delegation for {user_email}")
                return build('calendar', 'v3', credentials=delegated_credentials)

            logger.info(f"Using service account access for {user_email}")
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to create Google Calendar service for {user_email}: {str(e)}")
            raise

    def _should_delegate(self, user_email: str) -> bool:
        """Determine if domain-wide delegation should be used."""
        admin_domain = self._extract_domain(self.delegated_admin_email)
        user_domain = self._extract_domain(user_email)
        if not admin_domain or not user_domain:
            return False
        if self._is_consumer_domain(admin_domain) or self._is_consumer_domain(user_domain):
            return False
        return admin_domain == user_domain

    def _extract_domain(self, email: Optional[str]) -> Optional[str]:
        """Extract domain portion from an email address."""
        if not email or "@" not in email:
            return None
        return email.strip().split("@")[-1].lower()

    def _is_consumer_domain(self, domain: str) -> bool:
        """Return True for consumer email domains without delegation support."""
        return domain in {"gmail.com", "googlemail.com"}
    
    def create_event(
        self,
        doctor_email: str,
        patient_name: str,
        appointment_date: date,
        start_time: time,
        end_time: time,
        description: Optional[str] = None,
        timezone_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Google Calendar event for an appointment.
        Called AFTER database transaction succeeds.
        
        Args:
            doctor_email: Doctor's Google Calendar email
            patient_name: Patient's name
            appointment_date: Date of appointment
            start_time: Start time
            end_time: End time
            description: Optional description
            
        Returns:
            Google Calendar event ID if successful, None otherwise
        """
        try:
            service = self._get_service(doctor_email)
            
            try:
                tz = ZoneInfo(timezone_name) if timezone_name else timezone.utc
            except Exception:
                tz = timezone.utc
            start_datetime = datetime.combine(appointment_date, start_time).replace(tzinfo=tz)
            end_datetime = datetime.combine(appointment_date, end_time).replace(tzinfo=tz)
            
            # Format for Google Calendar (RFC3339)
            start_rfc3339 = start_datetime.isoformat()
            end_rfc3339 = end_datetime.isoformat()
            
            event = {
                'summary': f'Appointment: {patient_name}',
                'description': description or f'Appointment with {patient_name}',
                'start': {
                    'dateTime': start_rfc3339,
                    'timeZone': str(tz),
                },
                'end': {
                    'dateTime': end_rfc3339,
                    'timeZone': str(tz),
                },
            }
            
            event = self._execute_with_retry(
                lambda: service.events().insert(calendarId=doctor_email, body=event).execute()
            )
            
            logger.info(f"Created Google Calendar event {event.get('id')} for doctor {doctor_email}")
            return event.get('id')
            
        except HttpError as e:
            self.last_error = f"Google API error: {str(e)}"
            logger.error(f"Failed to create Google Calendar event: {self.last_error}")
            # Don't raise - Google Calendar is just a mirror
            return None
        except Exception as e:
            self.last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error creating Google Calendar event: {self.last_error}")
            return None
    
    def update_event(
        self,
        doctor_email: str,
        event_id: str,
        patient_name: str,
        appointment_date: date,
        start_time: time,
        end_time: time,
        description: Optional[str] = None,
        timezone_name: Optional[str] = None
    ) -> bool | str:
        """
        Update a Google Calendar event.
        Called when appointment is rescheduled.

        Args:
            doctor_email: Doctor's Google Calendar email
            event_id: Google Calendar event ID
            patient_name: Patient's name
            appointment_date: New date of appointment
            start_time: New start time
            end_time: New end time
            description: Optional description

        Returns:
            True if update successful, new event ID string if event was recreated,
            False if both update and create failed
        """
        try:
            service = self._get_service(doctor_email)

            # Get existing event with retry logic
            try:
                event = self._execute_with_retry(
                    lambda: service.events().get(
                        calendarId=doctor_email,
                        eventId=event_id
                    ).execute()
                )
            except HttpError as e:
                if e.resp.status == 404:
                    # Event was deleted from Google Calendar, create a new one
                    logger.warning(f"Google Calendar event {event_id} not found, creating new event")
                    new_event_id = self.create_event(
                        doctor_email=doctor_email,
                        patient_name=patient_name,
                        appointment_date=appointment_date,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        timezone_name=timezone_name
                    )
                    if new_event_id:
                        return new_event_id  # Return new ID so caller can update DB
                    return False
                raise  # Re-raise other HTTP errors

            try:
                tz = ZoneInfo(timezone_name) if timezone_name else timezone.utc
            except Exception:
                tz = timezone.utc
            start_datetime = datetime.combine(appointment_date, start_time).replace(tzinfo=tz)
            end_datetime = datetime.combine(appointment_date, end_time).replace(tzinfo=tz)

            start_rfc3339 = start_datetime.isoformat()
            end_rfc3339 = end_datetime.isoformat()

            event['summary'] = f'Appointment: {patient_name}'
            event['description'] = description or f'Appointment with {patient_name}'
            event['start']['dateTime'] = start_rfc3339
            event['end']['dateTime'] = end_rfc3339
            event['start']['timeZone'] = str(tz)
            event['end']['timeZone'] = str(tz)

            updated_event = self._execute_with_retry(
                lambda: service.events().update(calendarId=doctor_email, eventId=event_id, body=event).execute()
            )

            logger.info(f"Updated Google Calendar event {event_id} for doctor {doctor_email}")
            return True

        except HttpError as e:
            self.last_error = f"Google API error: {str(e)}"
            logger.error(f"Failed to update Google Calendar event: {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error updating Google Calendar event: {self.last_error}")
            return False
    
    def delete_event(self, doctor_email: str, event_id: str) -> bool:
        """
        Delete a Google Calendar event.
        Called when appointment is cancelled.
        
        Args:
            doctor_email: Doctor's Google Calendar email
            event_id: Google Calendar event ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service(doctor_email)
            
            self._execute_with_retry(
                lambda: service.events().delete(calendarId=doctor_email, eventId=event_id).execute()
            )
            
            logger.info(f"Deleted Google Calendar event {event_id} for doctor {doctor_email}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted, consider it success
                logger.warning(f"Google Calendar event {event_id} not found (already deleted?)")
                return True
            self.last_error = f"Google API error: {str(e)}"
            logger.error(f"Failed to delete Google Calendar event: {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error deleting Google Calendar event: {self.last_error}")
            return False

    def _execute_with_retry(self, func, max_attempts: int = 3, base_delay_seconds: int = 1):
        """Retry helper for transient Google Calendar API failures."""
        for attempt in range(max_attempts):
            try:
                return func()
            except HttpError as e:
                status = getattr(e.resp, "status", None)
                if status in {429, 500, 502, 503, 504} and attempt < max_attempts - 1:
                    delay = base_delay_seconds * (2 ** attempt)
                    time_module.sleep(delay)
                    continue
                raise
