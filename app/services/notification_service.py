"""
Notification Service - handles SMS notifications for doctors and patients.
Uses Twilio Content Templates API for DLT compliance in India.

Email notifications are commented out for now - can be enabled later.
"""
import json
import logging
from typing import Optional
from datetime import date, time

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending SMS notifications to doctors and patients using Twilio Content Templates."""

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

    def _send_sms_with_template(
        self,
        to_number: str,
        template_sid: str,
        content_variables: dict
    ) -> bool:
        """Send an SMS using Twilio Content Templates API."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug(f"SMS disabled, skipping message to {to_number}")
            return False

        if not to_number:
            logger.warning("Cannot send SMS: phone number is empty")
            return False

        if not template_sid:
            logger.warning("Cannot send SMS: template SID is not configured")
            return False

        try:
            normalized_number = self._normalize_phone_number(to_number)
            if not normalized_number:
                logger.warning(f"Cannot normalize phone number: {to_number}")
                return False

            # Send SMS using Content Templates API
            self.twilio_client.messages.create(
                from_=settings.TWILIO_PHONE_NUMBER,
                to=normalized_number,
                content_sid=template_sid,
                content_variables=json.dumps(content_variables)
            )

            logger.info(f"SMS sent successfully to {normalized_number} using template {template_sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return False

    # ==================== DOCTOR SMS NOTIFICATIONS ====================

    def send_doctor_booking_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time,
        symptoms: Optional[str] = None
    ) -> bool:
        """Send booking confirmation SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return False

        template_sid = settings.TWILIO_TEMPLATE_DOCTOR_BOOKING
        if not template_sid:
            logger.warning("Doctor booking template not configured")
            return False

        # Content variables must match the template placeholders
        # Template format: New Appointment! Patient: {{1}}, Mobile: {{2}}, Date: {{3}}, Time: {{4}}, Symptoms: {{5}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time),
            "5": symptoms or "Not specified"
        }

        return self._send_sms_with_template(doctor_phone, template_sid, content_variables)

    def send_doctor_reschedule_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        old_date: date,
        old_time: time,
        new_date: date,
        new_time: time
    ) -> bool:
        """Send reschedule notification SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return False

        template_sid = settings.TWILIO_TEMPLATE_DOCTOR_RESCHEDULE
        if not template_sid:
            logger.warning("Doctor reschedule template not configured")
            return False

        # Template format: Appointment Rescheduled! Patient: {{1}}, Mobile: {{2}}, Old: {{3}} {{4}}, New: {{5}} {{6}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(old_date),
            "4": self._format_time(old_time),
            "5": self._format_date(new_date),
            "6": self._format_time(new_time)
        }

        return self._send_sms_with_template(doctor_phone, template_sid, content_variables)

    def send_doctor_cancellation_sms(
        self,
        doctor_phone: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time
    ) -> bool:
        """Send cancellation notification SMS to doctor using Content Template."""
        if not doctor_phone:
            logger.debug(f"Doctor {doctor_name} has no phone number, skipping SMS")
            return False

        template_sid = settings.TWILIO_TEMPLATE_DOCTOR_CANCEL
        if not template_sid:
            logger.warning("Doctor cancellation template not configured")
            return False

        # Template format: Appointment Cancelled! Patient: {{1}}, Mobile: {{2}}, Was: {{3}} {{4}}
        content_variables = {
            "1": patient_name,
            "2": patient_mobile,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time)
        }

        return self._send_sms_with_template(doctor_phone, template_sid, content_variables)

    # ==================== PATIENT SMS NOTIFICATIONS ====================

    def send_patient_booking_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        doctor_specialization: str,
        appointment_date: date,
        appointment_time: time,
        clinic_address: Optional[str] = None
    ) -> bool:
        """Send booking confirmation SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return False

        template_sid = settings.TWILIO_TEMPLATE_PATIENT_BOOKING
        if not template_sid:
            logger.warning("Patient booking template not configured")
            return False

        # Template format: Dear {{1}}, Appointment Confirmed! Doctor: Dr. {{2}} ({{3}}), Date: {{4}}, Time: {{5}}, Location: {{6}}
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": doctor_specialization,
            "4": self._format_date(appointment_date),
            "5": self._format_time(appointment_time),
            "6": clinic_address or settings.CLINIC_ADDRESS or "Contact clinic"
        }

        return self._send_sms_with_template(patient_mobile, template_sid, content_variables)

    def send_patient_reschedule_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        doctor_specialization: str,
        new_date: date,
        new_time: time,
        clinic_address: Optional[str] = None
    ) -> bool:
        """Send reschedule notification SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return False

        template_sid = settings.TWILIO_TEMPLATE_PATIENT_RESCHEDULE
        if not template_sid:
            logger.warning("Patient reschedule template not configured")
            return False

        # Template format: Dear {{1}}, Appointment Rescheduled. Doctor: Dr. {{2}} ({{3}}), New Date: {{4}}, New Time: {{5}}, Location: {{6}}
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": doctor_specialization,
            "4": self._format_date(new_date),
            "5": self._format_time(new_time),
            "6": clinic_address or settings.CLINIC_ADDRESS or "Contact clinic"
        }

        return self._send_sms_with_template(patient_mobile, template_sid, content_variables)

    def send_patient_cancellation_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: date,
        appointment_time: time
    ) -> bool:
        """Send cancellation notification SMS to patient using Content Template."""
        if not patient_mobile:
            logger.warning("Cannot send patient SMS: mobile number is empty")
            return False

        template_sid = settings.TWILIO_TEMPLATE_PATIENT_CANCEL
        if not template_sid:
            logger.warning("Patient cancellation template not configured")
            return False

        # Template format: Dear {{1}}, Your appointment with Dr. {{2}} on {{3}} at {{4}} has been cancelled.
        content_variables = {
            "1": patient_name,
            "2": doctor_name,
            "3": self._format_date(appointment_date),
            "4": self._format_time(appointment_time)
        }

        return self._send_sms_with_template(patient_mobile, template_sid, content_variables)


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
