"""
Notification Service - handles SMS notifications for doctors and patients.
Uses Twilio Content Templates API for DLT compliance in India.

Features:
- Async SMS sending (non-blocking)
- Delivery status tracking with message SID
- Template variable validation
- Retry logic with exponential backoff
- SMS opt-out support
- Structured logging

Email notifications are commented out for now - can be enabled later.
"""
import json
import logging
import threading
from typing import Optional, Dict, Any, Tuple
from datetime import date, time
from dataclasses import dataclass
from enum import Enum

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    DOCTOR_BOOKING = "doctor_booking"
    DOCTOR_RESCHEDULE = "doctor_reschedule"
    DOCTOR_CANCEL = "doctor_cancel"
    PATIENT_BOOKING = "patient_booking"
    PATIENT_RESCHEDULE = "patient_reschedule"
    PATIENT_CANCEL = "patient_cancel"


@dataclass
class SMSResult:
    """Result of an SMS send operation."""
    success: bool
    message_sid: Optional[str] = None
    error: Optional[str] = None
    to_number: Optional[str] = None
    notification_type: Optional[str] = None


class NotificationService:
    """Service for sending SMS notifications to doctors and patients using Twilio Content Templates."""

    # Template variable counts for validation
    TEMPLATE_VARIABLE_COUNTS = {
        NotificationType.DOCTOR_BOOKING: 5,      # patient_name, mobile, date, time, symptoms
        NotificationType.DOCTOR_RESCHEDULE: 6,   # patient_name, mobile, old_date, old_time, new_date, new_time
        NotificationType.DOCTOR_CANCEL: 4,       # patient_name, mobile, date, time
        NotificationType.PATIENT_BOOKING: 6,     # name, doctor, specialization, date, time, location
        NotificationType.PATIENT_RESCHEDULE: 6,  # name, doctor, specialization, date, time, location
        NotificationType.PATIENT_CANCEL: 4,      # name, doctor, date, time
    }

    # Max retry attempts for transient failures
    MAX_RETRIES = 3
    # Base delay in seconds for exponential backoff
    RETRY_BASE_DELAY = 1

    def __init__(self):
        self.sms_enabled = settings.SMS_NOTIFICATIONS_ENABLED
        self.twilio_client = None

        if self.sms_enabled:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.sms_enabled = False

    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number to E.164 format for Twilio."""
        if not phone:
            return ""

        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))

        # Handle Indian phone numbers
        if len(digits) == 10:
            # Assume Indian number, add +91
            return f"+91{digits}"
        elif len(digits) == 11 and digits.startswith('0'):
            # Remove leading 0, add +91
            return f"+91{digits[1:]}"
        elif len(digits) == 12 and digits.startswith('91'):
            # Already has country code, add +
            return f"+{digits}"
        elif len(digits) > 10 and not phone.startswith('+'):
            # Assume it has country code
            return f"+{digits}"

        return f"+{digits}" if not phone.startswith('+') else phone

    def _format_time(self, t: time) -> str:
        """Format time for display (12-hour format)."""
        return t.strftime("%I:%M %p")

    def _format_date(self, d: date) -> str:
        """Format date for display."""
        return d.strftime("%B %d, %Y")

    def _validate_template_variables(
        self,
        notification_type: NotificationType,
        content_variables: Dict[str, str]
    ) -> Tuple[bool, Optional[str]]:
        """Validate that content variables match template requirements."""
        expected_count = self.TEMPLATE_VARIABLE_COUNTS.get(notification_type)
        if expected_count is None:
            return False, f"Unknown notification type: {notification_type}"

        actual_count = len(content_variables)
        if actual_count != expected_count:
            return False, f"Expected {expected_count} variables, got {actual_count}"

        # Check for empty values
        for key, value in content_variables.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"Variable '{key}' is empty or None"

        return True, None

    def _get_template_sid(self, notification_type: NotificationType) -> Optional[str]:
        """Get the template SID for a notification type."""
        template_map = {
            NotificationType.DOCTOR_BOOKING: settings.TWILIO_TEMPLATE_DOCTOR_BOOKING,
            NotificationType.DOCTOR_RESCHEDULE: settings.TWILIO_TEMPLATE_DOCTOR_RESCHEDULE,
            NotificationType.DOCTOR_CANCEL: settings.TWILIO_TEMPLATE_DOCTOR_CANCEL,
            NotificationType.PATIENT_BOOKING: settings.TWILIO_TEMPLATE_PATIENT_BOOKING,
            NotificationType.PATIENT_RESCHEDULE: settings.TWILIO_TEMPLATE_PATIENT_RESCHEDULE,
            NotificationType.PATIENT_CANCEL: settings.TWILIO_TEMPLATE_PATIENT_CANCEL,
        }
        return template_map.get(notification_type)

    def _send_sms_with_retry(
        self,
        to_number: str,
        template_sid: str,
        content_variables: Dict[str, str],
        notification_type: NotificationType
    ) -> SMSResult:
        """Send SMS with retry logic for transient failures."""
        import time as time_module

        normalized_number = self._normalize_phone_number(to_number)
        if not normalized_number:
            return SMSResult(
                success=False,
                error=f"Cannot normalize phone number: {to_number}",
                to_number=to_number,
                notification_type=notification_type.value
            )

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                message = self.twilio_client.messages.create(
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=normalized_number,
                    content_sid=template_sid,
                    content_variables=json.dumps(content_variables)
                )

                logger.info(
                    "SMS sent successfully",
                    extra={
                        "message_sid": message.sid,
                        "to": normalized_number,
                        "notification_type": notification_type.value,
                        "template_sid": template_sid,
                        "attempt": attempt + 1
                    }
                )

                return SMSResult(
                    success=True,
                    message_sid=message.sid,
                    to_number=normalized_number,
                    notification_type=notification_type.value
                )

            except Exception as e:
                last_error = str(e)
                error_str = str(e).lower()

                # Check if error is retryable (network/timeout issues)
                retryable_errors = ['timeout', 'connection', 'temporarily', '503', '502', '504']
                is_retryable = any(err in error_str for err in retryable_errors)

                if is_retryable and attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"SMS send failed (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {delay}s",
                        extra={
                            "to": normalized_number,
                            "error": last_error,
                            "notification_type": notification_type.value
                        }
                    )
                    time_module.sleep(delay)
                else:
                    # Non-retryable error or max retries reached
                    break

        logger.error(
            f"Failed to send SMS after {self.MAX_RETRIES} attempts",
            extra={
                "to": normalized_number,
                "error": last_error,
                "notification_type": notification_type.value,
                "template_sid": template_sid
            }
        )

        return SMSResult(
            success=False,
            error=last_error,
            to_number=normalized_number,
            notification_type=notification_type.value
        )

    def _send_sms_with_template(
        self,
        to_number: str,
        notification_type: NotificationType,
        content_variables: Dict[str, str],
        async_send: bool = True
    ) -> SMSResult:
        """Send an SMS using Twilio Content Templates API."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug(f"SMS disabled, skipping message to {to_number}")
            return SMSResult(success=False, error="SMS notifications disabled")

        if not to_number:
            logger.warning("Cannot send SMS: phone number is empty")
            return SMSResult(success=False, error="Phone number is empty")

        template_sid = self._get_template_sid(notification_type)
        if not template_sid:
            logger.warning(f"Template not configured for {notification_type.value}")
            return SMSResult(success=False, error=f"Template not configured: {notification_type.value}")

        # Validate template variables
        is_valid, validation_error = self._validate_template_variables(notification_type, content_variables)
        if not is_valid:
            logger.warning(f"Template variable validation failed: {validation_error}")
            return SMSResult(success=False, error=validation_error)

        if async_send:
            # Send asynchronously in a background thread
            thread = threading.Thread(
                target=self._send_sms_with_retry,
                args=(to_number, template_sid, content_variables, notification_type),
                daemon=True
            )
            thread.start()
            logger.debug(f"SMS queued for async delivery to {to_number}")
            return SMSResult(success=True, error=None, to_number=to_number, notification_type=notification_type.value)
        else:
            # Send synchronously
            return self._send_sms_with_retry(to_number, template_sid, content_variables, notification_type)

    # ==================== DOCTOR SMS NOTIFICATIONS ====================

    def send_doctor_booking_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time,
        symptoms: Optional[str] = None,
        async_send: bool = True
    ) -> SMSResult:
        """Send booking confirmation SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        # Content variables must match the template placeholders
        # Template format: New Appointment! Patient: {{1}}, Mobile: {{2}}, Date: {{3}}, Time: {{4}}, Symptoms: {{5}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time),
            "5": symptoms or "Not specified"
        }

        return self._send_sms_with_template(
            doctor_phone,
            NotificationType.DOCTOR_BOOKING,
            content_variables,
            async_send
        )

    def send_doctor_reschedule_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        old_date: date,
        old_time: time,
        new_date: date,
        new_time: time,
        async_send: bool = True
    ) -> SMSResult:
        """Send reschedule notification SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        # Template format: Appointment Rescheduled! Patient: {{1}}, Mobile: {{2}}, Old: {{3}} {{4}}, New: {{5}} {{6}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(old_date),
            "4": self._format_time(old_time),
            "5": self._format_date(new_date),
            "6": self._format_time(new_time)
        }

        return self._send_sms_with_template(
            doctor_phone,
            NotificationType.DOCTOR_RESCHEDULE,
            content_variables,
            async_send
        )

    def send_doctor_cancellation_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time,
        async_send: bool = True
    ) -> SMSResult:
        """Send cancellation notification SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        # Template format: Appointment Cancelled! Patient: {{1}}, Mobile: {{2}}, Was: {{3}} {{4}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time)
        }

        return self._send_sms_with_template(
            doctor_phone,
            NotificationType.DOCTOR_CANCEL,
            content_variables,
            async_send
        )

    # ==================== PATIENT SMS NOTIFICATIONS ====================

    def send_patient_booking_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        doctor_specialization: str,
        appointment_date: date,
        appointment_time: time,
        clinic_address: Optional[str] = None,
        sms_opt_in: bool = True,
        async_send: bool = True
    ) -> SMSResult:
        """Send booking confirmation SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        # Template format: Dear {{1}}, Appointment Confirmed! Doctor: Dr. {{2}} ({{3}}), Date: {{4}}, Time: {{5}}, Location: {{6}}
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": doctor_specialization,
            "4": self._format_date(appointment_date),
            "5": self._format_time(appointment_time),
            "6": clinic_address or settings.CLINIC_ADDRESS or "Contact clinic"
        }

        return self._send_sms_with_template(
            patient_mobile,
            NotificationType.PATIENT_BOOKING,
            content_variables,
            async_send
        )

    def send_patient_reschedule_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        doctor_specialization: str,
        new_date: date,
        new_time: time,
        clinic_address: Optional[str] = None,
        sms_opt_in: bool = True,
        async_send: bool = True
    ) -> SMSResult:
        """Send reschedule notification SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        # Template format: Dear {{1}}, Appointment Rescheduled. Doctor: Dr. {{2}} ({{3}}), New Date: {{4}}, New Time: {{5}}, Location: {{6}}
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": doctor_specialization,
            "4": self._format_date(new_date),
            "5": self._format_time(new_time),
            "6": clinic_address or settings.CLINIC_ADDRESS or "Contact clinic"
        }

        return self._send_sms_with_template(
            patient_mobile,
            NotificationType.PATIENT_RESCHEDULE,
            content_variables,
            async_send
        )

    def send_patient_cancellation_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: date,
        appointment_time: time,
        sms_opt_in: bool = True,
        async_send: bool = True
    ) -> SMSResult:
        """Send cancellation notification SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        # Template format: Dear {{1}}, Your appointment with Dr. {{2}} on {{3}} at {{4}} has been cancelled.
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time)
        }

        return self._send_sms_with_template(
            patient_mobile,
            NotificationType.PATIENT_CANCEL,
            content_variables,
            async_send
        )


# Singleton instance
notification_service = NotificationService()


# ==================== EMAIL NOTIFICATIONS (COMMENTED OUT FOR NOW) ====================
# To enable email notifications, uncomment the following code and set EMAIL_NOTIFICATIONS_ENABLED=True
#
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
#
# # Add to __init__:
# # self.email_enabled = settings.EMAIL_NOTIFICATIONS_ENABLED
#
# def send_doctor_booking_email(self, doctor_email, doctor_name, patient_name, patient_mobile, appointment_date, appointment_time, symptoms=None):
#     if not self.email_enabled:
#         return False
#     subject = f"New Appointment: {patient_name}"
#     html_content = f"<html><body><h2>New Appointment</h2><p>Patient: {patient_name}</p></body></html>"
#     return self._send_email(doctor_email, subject, html_content)
#
# def _send_email(self, to_email, subject, html_content):
#     try:
#         msg = MIMEMultipart('alternative')
#         msg['Subject'] = subject
#         msg['From'] = settings.SMTP_FROM_EMAIL
#         msg['To'] = to_email
#         msg.attach(MIMEText(html_content, 'html'))
#         with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
#             server.starttls()
#             server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
#             server.send_message(msg)
#         return True
#     except Exception as e:
#         logger.error(f"Failed to send email: {e}")
#         return False
