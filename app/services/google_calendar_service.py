"""
Google Calendar Service - syncs appointments with Google Calendar.
Google Calendar is ONLY a mirror of confirmed appointments.
Never reads availability from Google Calendar.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, date, time
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""
    
    def __init__(self):
        """Initialize Google Calendar service with service account credentials."""
        self.credentials_path = settings.GOOGLE_CALENDAR_CREDENTIALS_PATH
        self.delegated_admin_email = settings.GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL
        self._service = None
    
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
        description: Optional[str] = None
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
            
            # Combine date and time (assume UTC timezone)
            from datetime import timezone
            start_datetime = datetime.combine(appointment_date, start_time).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(appointment_date, end_time).replace(tzinfo=timezone.utc)
            
            # Format for Google Calendar (RFC3339)
            start_rfc3339 = start_datetime.isoformat()
            end_rfc3339 = end_datetime.isoformat()
            
            event = {
                'summary': f'Appointment: {patient_name}',
                'description': description or f'Appointment with {patient_name}',
                'start': {
                    'dateTime': start_rfc3339,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_rfc3339,
                    'timeZone': 'UTC',
                },
            }
            
            event = service.events().insert(
                calendarId=doctor_email,
                body=event
            ).execute()
            
            logger.info(f"Created Google Calendar event {event.get('id')} for doctor {doctor_email}")
            return event.get('id')
            
        except HttpError as e:
            logger.error(f"Failed to create Google Calendar event: {str(e)}")
            # Don't raise - Google Calendar is just a mirror
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Google Calendar event: {str(e)}")
            return None
    
    def update_event(
        self,
        doctor_email: str,
        event_id: str,
        patient_name: str,
        appointment_date: date,
        start_time: time,
        end_time: time,
        description: Optional[str] = None
    ) -> bool:
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
            True if successful, False otherwise
        """
        try:
            service = self._get_service(doctor_email)
            
            # Get existing event
            event = service.events().get(
                calendarId=doctor_email,
                eventId=event_id
            ).execute()
            
            # Update event details (assume UTC timezone)
            from datetime import timezone
            start_datetime = datetime.combine(appointment_date, start_time).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(appointment_date, end_time).replace(tzinfo=timezone.utc)
            
            start_rfc3339 = start_datetime.isoformat()
            end_rfc3339 = end_datetime.isoformat()
            
            event['summary'] = f'Appointment: {patient_name}'
            event['description'] = description or f'Appointment with {patient_name}'
            event['start']['dateTime'] = start_rfc3339
            event['end']['dateTime'] = end_rfc3339
            
            updated_event = service.events().update(
                calendarId=doctor_email,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Updated Google Calendar event {event_id} for doctor {doctor_email}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to update Google Calendar event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating Google Calendar event: {str(e)}")
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
            
            service.events().delete(
                calendarId=doctor_email,
                eventId=event_id
            ).execute()
            
            logger.info(f"Deleted Google Calendar event {event_id} for doctor {doctor_email}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted, consider it success
                logger.warning(f"Google Calendar event {event_id} not found (already deleted?)")
                return True
            logger.error(f"Failed to delete Google Calendar event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting Google Calendar event: {str(e)}")
            return False
