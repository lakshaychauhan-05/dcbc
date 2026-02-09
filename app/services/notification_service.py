"""
Notification Service - handles email notifications for doctors and SMS notifications for patients.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import date, time

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email and SMS notifications."""

    def __init__(self):
        self.email_enabled = settings.EMAIL_NOTIFICATIONS_ENABLED
        self.sms_enabled = settings.SMS_NOTIFICATIONS_ENABLED
        self.twilio_client = None

        if self.sms_enabled:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.sms_enabled = False

    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number to E.164 format for Twilio."""
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
        elif len(digits) > 10 and not digits.startswith('+'):
            # Assume it has country code
            return f"+{digits}"

        return f"+{digits}" if not phone.startswith('+') else phone

    def _format_time(self, t: time) -> str:
        """Format time for display (12-hour format)."""
        return t.strftime("%I:%M %p")

    def _format_date(self, d: date) -> str:
        """Format date for display."""
        return d.strftime("%B %d, %Y")

    # ==================== DOCTOR EMAIL NOTIFICATIONS ====================

    def send_doctor_booking_email(
        self,
        doctor_email: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time,
        symptoms: Optional[str] = None
    ) -> bool:
        """Send booking confirmation email to doctor."""
        if not self.email_enabled:
            logger.debug("Email notifications disabled, skipping doctor booking email")
            return False

        subject = f"New Appointment: {patient_name} on {self._format_date(appointment_date)}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2c5aa0;">New Appointment Booked</h2>
            <p>Dear Dr. {doctor_name},</p>
            <p>A new appointment has been booked with the following details:</p>
            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Patient Name:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Mobile:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_mobile}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Date:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self._format_date(appointment_date)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Time:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self._format_time(appointment_time)}</td>
                </tr>
                {f'<tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Symptoms:</td><td style="padding: 8px; border: 1px solid #ddd;">{symptoms}</td></tr>' if symptoms else ''}
            </table>
            <p>Best regards,<br>{settings.CLINIC_NAME}</p>
        </body>
        </html>
        """

        return self._send_email(doctor_email, subject, html_content)

    def send_doctor_reschedule_email(
        self,
        doctor_email: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        old_date: date,
        old_time: time,
        new_date: date,
        new_time: time
    ) -> bool:
        """Send reschedule notification email to doctor."""
        if not self.email_enabled:
            logger.debug("Email notifications disabled, skipping doctor reschedule email")
            return False

        subject = f"Appointment Rescheduled: {patient_name}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #e67e22;">Appointment Rescheduled</h2>
            <p>Dear Dr. {doctor_name},</p>
            <p>An appointment has been rescheduled:</p>
            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Patient Name:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Mobile:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_mobile}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Original Date/Time:</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-decoration: line-through; color: #999;">{self._format_date(old_date)} at {self._format_time(old_time)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">New Date/Time:</td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #27ae60; font-weight: bold;">{self._format_date(new_date)} at {self._format_time(new_time)}</td>
                </tr>
            </table>
            <p>Best regards,<br>{settings.CLINIC_NAME}</p>
        </body>
        </html>
        """

        return self._send_email(doctor_email, subject, html_content)

    def send_doctor_cancellation_email(
        self,
        doctor_email: str,
        doctor_name: str,
        patient_name: str,
        patient_mobile: str,
        appointment_date: date,
        appointment_time: time
    ) -> bool:
        """Send cancellation notification email to doctor."""
        if not self.email_enabled:
            logger.debug("Email notifications disabled, skipping doctor cancellation email")
            return False

        subject = f"Appointment Cancelled: {patient_name} on {self._format_date(appointment_date)}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #c0392b;">Appointment Cancelled</h2>
            <p>Dear Dr. {doctor_name},</p>
            <p>The following appointment has been cancelled:</p>
            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Patient Name:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Mobile:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{patient_mobile}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Date:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self._format_date(appointment_date)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Time:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self._format_time(appointment_time)}</td>
                </tr>
            </table>
            <p>This time slot is now available for other patients.</p>
            <p>Best regards,<br>{settings.CLINIC_NAME}</p>
        </body>
        </html>
        """

        return self._send_email(doctor_email, subject, html_content)

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email using SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
            msg['To'] = to_email

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    # ==================== PATIENT SMS NOTIFICATIONS ====================

    def send_patient_booking_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: date,
        appointment_time: time,
        clinic_address: Optional[str] = None
    ) -> bool:
        """Send booking confirmation SMS to patient."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug("SMS notifications disabled, skipping patient booking SMS")
            return False

        clinic_info = f"\nLocation: {clinic_address}" if clinic_address else ""

        message = (
            f"Dear {patient_name}, your appointment with Dr. {doctor_name} is confirmed for "
            f"{self._format_date(appointment_date)} at {self._format_time(appointment_time)}."
            f"{clinic_info}\n- {settings.CLINIC_NAME}"
        )

        return self._send_sms(patient_mobile, message)

    def send_patient_reschedule_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        new_date: date,
        new_time: time,
        clinic_address: Optional[str] = None
    ) -> bool:
        """Send reschedule notification SMS to patient."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug("SMS notifications disabled, skipping patient reschedule SMS")
            return False

        clinic_info = f"\nLocation: {clinic_address}" if clinic_address else ""

        message = (
            f"Dear {patient_name}, your appointment with Dr. {doctor_name} has been rescheduled to "
            f"{self._format_date(new_date)} at {self._format_time(new_time)}."
            f"{clinic_info}\n- {settings.CLINIC_NAME}"
        )

        return self._send_sms(patient_mobile, message)

    def send_patient_cancellation_sms(
        self,
        patient_mobile: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: date,
        appointment_time: time
    ) -> bool:
        """Send cancellation notification SMS to patient."""
        if not self.sms_enabled or not self.twilio_client:
            logger.debug("SMS notifications disabled, skipping patient cancellation SMS")
            return False

        message = (
            f"Dear {patient_name}, your appointment with Dr. {doctor_name} on "
            f"{self._format_date(appointment_date)} at {self._format_time(appointment_time)} "
            f"has been cancelled. Please contact us to reschedule.\n- {settings.CLINIC_NAME}"
        )

        return self._send_sms(patient_mobile, message)

    def _send_sms(self, to_number: str, message: str) -> bool:
        """Send an SMS using Twilio."""
        try:
            normalized_number = self._normalize_phone_number(to_number)

            self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=normalized_number
            )

            logger.info(f"SMS sent successfully to {normalized_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return False


# Singleton instance
notification_service = NotificationService()
