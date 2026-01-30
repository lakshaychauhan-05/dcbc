"""
Client service for communicating with the Calendar Booking Service.
"""
import json
import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import date, time

from app.core.config import settings
from app.middleware.request_id import get_request_id

logger = logging.getLogger(__name__)


def _parse_error_detail(response: Optional[httpx.Response]) -> Optional[str]:
    """Extract 'detail' from API error response body (JSON)."""
    if not response or not response.text:
        return None
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            d = body["detail"]
            return d if isinstance(d, str) else json.dumps(d)
    except Exception:
        pass
    return None


class CalendarClient:
    """Client for interacting with the Calendar Booking Service."""

    def __init__(self):
        self.base_url = settings.CALENDAR_SERVICE_URL.rstrip("/")
        self.api_key = settings.CALENDAR_SERVICE_API_KEY
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-API-Key": self.api_key}
        )

    def _build_headers(self, idempotency_key: Optional[str] = None) -> Optional[Dict[str, str]]:
        headers: Dict[str, str] = {}
        request_id = get_request_id()
        if request_id and request_id != "-":
            headers["X-Request-ID"] = request_id
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers or None

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
                params=params,
                headers=self._build_headers()
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
                    logger.error("Authentication failed. Check API key configuration.")
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
                params=params,
                headers=self._build_headers()
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
                params={"date": date.isoformat()},
                headers=self._build_headers()
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting doctor availability: {e}")
            return {"available_slots": [], "error": str(e)}

    async def book_appointment(self, booking_data: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Book an appointment."""
        try:
            headers = self._build_headers(idempotency_key)
            response = await self.client.post(
                f"{self.base_url}/api/v1/appointments/",
                json=booking_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error booking appointment: {e}")
            response = getattr(e, "response", None)
            detail = _parse_error_detail(response)
            return {
                "error": str(e),
                "details": response.text if response else None,
                "detail": detail,
            }

    async def get_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Get appointment details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/appointments/{appointment_id}",
                headers=self._build_headers()
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting appointment: {e}")
            return {"error": str(e)}

    async def reschedule_appointment(self, appointment_id: str, reschedule_data: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Reschedule an appointment."""
        try:
            headers = self._build_headers(idempotency_key)
            response = await self.client.put(
                f"{self.base_url}/api/v1/appointments/{appointment_id}/reschedule",
                json=reschedule_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {"error": str(e)}

    async def cancel_appointment(self, appointment_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an appointment."""
        try:
            headers = self._build_headers(idempotency_key)
            response = await self.client.delete(
                f"{self.base_url}/api/v1/appointments/{appointment_id}",
                headers=headers
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
                f"{self.base_url}/api/v1/appointments/patient/{patient_id}",
                headers=self._build_headers()
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting patient appointments: {e}")
            return []

    async def get_patient_by_mobile(self, mobile_number: str) -> Dict[str, Any]:
        """Get patient by mobile number."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/patients/mobile/{mobile_number}",
                headers=self._build_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting patient by mobile: {e}")
            return {"error": str(e)}

    def is_available(self) -> bool:
        """Check if calendar service is available."""
        return bool(self.base_url and self.api_key)