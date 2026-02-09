"""
Notification Service - handles SMS notifications for doctors and patients.
Uses Twilio SMS API with direct message body for proper variable substitution.

Features:
- Async SMS sending (non-blocking)
- Delivery status tracking with message SID
- Retry logic with exponential backoff
- SMS opt-out support
- Structured logging

Email notifications are commented out for now - can be enabled later.
"""
import logging
import threading
from typing import Optional
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
    """Service for sending SMS notifications to doctors and patients using Twilio."""

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

    def _send_sms_with_retry(
        self,
        to_number: str,
        body: str,
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
                    body=body
                )

                logger.info(
                    "SMS sent successfully",
                    extra={
                        "message_sid": message.sid,
                        "to": normalized_number,
                        "notification_type": notification_type.value,
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
                "notification_type": notification_type.value
            }
        )

        return SMSResult(
            success=False,
            error=last_error,
            to_number=normalized_number,
            notification_type=notification_type.value
        )

    def _send_sms(
        self,
        to_number: str,
        body: str,
        notification_type: NotificationType,
        async_send: bool = True
    ) -> SMSResult:
        """Send an SMS using Twilio."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug(f"SMS disabled, skipping message to {to_number}")
            return SMSResult(success=False, error="SMS notifications disabled")

        if not to_number:
            logger.warning("Cannot send SMS: phone number is empty")
            return SMSResult(success=False, error="Phone number is empty")

        if async_send:
            # Send asynchronously in a background thread
            thread = threading.Thread(
                target=self._send_sms_with_retry,
                args=(to_number, body, notification_type),
                daemon=True
            )
            thread.start()
            logger.info(f"SMS queued for async delivery to {to_number}")
            return SMSResult(success=True, error=None, to_number=to_number, notification_type=notification_type.value)
        else:
            # Send synchronously
            return self._send_sms_with_retry(to_number, body, notification_type)

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
        """Send booking confirmation SMS to doctor."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        body = (
            f"New Appointment!\n"
            f"Patient: {patient_name}\n"
            f"Mobile: {patient_mobile}\n"
            f"Date: {self._format_date(appointment_date)}\n"
            f"Time: {self._format_time(appointment_time)}\n"
            f"Symptoms: {symptoms or 'Not specified'}"
        )

        return self._send_sms(
            doctor_phone,
            body,
            NotificationType.DOCTOR_BOOKING,
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
        """Send reschedule notification SMS to doctor."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        body = (
            f"Appointment Rescheduled!\n"
            f"Patient: {patient_name}\n"
            f"Mobile: {patient_mobile}\n"
            f"Old: {self._format_date(old_date)} {self._format_time(old_time)}\n"
            f"New: {self._format_date(new_date)} {self._format_time(new_time)}"
        )

        return self._send_sms(
            doctor_phone,
            body,
            NotificationType.DOCTOR_RESCHEDULE,
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
        """Send cancellation notification SMS to doctor."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return SMSResult(success=False, error="Doctor phone number not available")

        body = (
            f"Appointment Cancelled!\n"
            f"Patient: {patient_name}\n"
            f"Mobile: {patient_mobile}\n"
            f"Was: {self._format_date(appointment_date)} {self._format_time(appointment_time)}"
        )

        return self._send_sms(
            doctor_phone,
            body,
            NotificationType.DOCTOR_CANCEL,
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
        """Send booking confirmation SMS to patient."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        location = clinic_address or settings.CLINIC_ADDRESS or "Contact clinic for address"

        body = (
            f"Dear {patient_name},\n"
            f"Appointment Confirmed!\n"
            f"Doctor: Dr. {doctor_name} ({doctor_specialization})\n"
            f"Date: {self._format_date(appointment_date)}\n"
            f"Time: {self._format_time(appointment_time)}\n"
            f"Location: {location}"
        )

        return self._send_sms(
            patient_mobile,
            body,
            NotificationType.PATIENT_BOOKING,
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
        """Send reschedule notification SMS to patient."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        location = clinic_address or settings.CLINIC_ADDRESS or "Contact clinic for address"

        body = (
            f"Dear {patient_name},\n"
            f"Appointment Rescheduled.\n"
            f"Doctor: Dr. {doctor_name} ({doctor_specialization})\n"
            f"New Date: {self._format_date(new_date)}\n"
            f"New Time: {self._format_time(new_time)}\n"
            f"Location: {location}"
        )

        return self._send_sms(
            patient_mobile,
            body,
            NotificationType.PATIENT_RESCHEDULE,
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
        """Send cancellation notification SMS to patient."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return SMSResult(success=False, error="Patient mobile number is empty")

        if not sms_opt_in:
            logger.debug(f"Patient {patient_name} has opted out of SMS notifications")
            return SMSResult(success=False, error="Patient opted out of SMS")

        body = (
            f"Dear {patient_name},\n"
            f"Your appointment with Dr. {doctor_name} on "
            f"{self._format_date(appointment_date)} at {self._format_time(appointment_time)} "
            f"has been cancelled."
        )

        return self._send_sms(
            patient_mobile,
            body,
            NotificationType.PATIENT_CANCEL,
            async_send
        )


# Singleton instance
notification_service = NotificationService()
