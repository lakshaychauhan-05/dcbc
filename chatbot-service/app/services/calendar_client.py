"""
Client service for communicating with the Calendar Booking Service.
"""
import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import date, time

from app.core.config import settings

logger = logging.getLogger(__name__)


class CalendarClient:
    """Client for interacting with the Calendar Booking Service."""

    def __init__(self):
        self.base_url = settings.CALENDAR_SERVICE_URL.rstrip("/")
        self.api_key = settings.CALENDAR_SERVICE_API_KEY
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-API-Key": self.api_key}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_doctor_data(self, clinic_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch doctor data from calendar service."""
        try:
            params = {}
            if clinic_id:
                params["clinic_id"] = clinic_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/doctors/export",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error fetching doctor data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                error_detail = e.response.text
                logger.error(f"HTTP Status: {status_code}, Detail: {error_detail}")
                if status_code == 401:
                    logger.error(f"Authentication failed. Check API key. Using key: {self.api_key[:10]}...")
                    logger.error(f"Calendar service URL: {self.base_url}")
            return {"doctors": [], "error": str(e)}

    async def check_availability(
        self,
        date: date,
        specialization: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check doctor availability."""
        try:
            params = {
                "specialization": specialization,
                "language": language,
                "date": date.isoformat()
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/availability-search",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error checking availability: {e}")
            return {"doctors": [], "error": str(e)}

    async def get_doctor_availability(
        self,
        doctor_email: str,
        date: date
    ) -> Dict[str, Any]:
        """Get availability for a specific doctor."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/availability/{doctor_email}",
                params={"date": date.isoformat()}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting doctor availability: {e}")
            return {"available_slots": [], "error": str(e)}

    async def book_appointment(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Book an appointment."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/appointments/",
                json=booking_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error booking appointment: {e}")
            return {"error": str(e), "details": e.response.text if hasattr(e, 'response') else None}

    async def get_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Get appointment details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/{appointment_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting appointment: {e}")
            return {"error": str(e)}

    async def reschedule_appointment(self, appointment_id: str, reschedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reschedule an appointment."""
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/appointments/{appointment_id}/reschedule",
                json=reschedule_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {"error": str(e)}

    async def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Cancel an appointment."""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/appointments/{appointment_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {"error": str(e)}

    async def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a patient."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/patient/{patient_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting patient appointments: {e}")
            return []

    def is_available(self) -> bool:
        """Check if calendar service is available."""
        return bool(self.base_url and self.api_key)