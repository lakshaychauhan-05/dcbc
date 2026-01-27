"""
RAG Sync Service - syncs descriptive doctor data to RAG service.
RAG is READ-ONLY and stores ONLY descriptive doctor data.
Never sends schedule, slots, or availability.
"""
import httpx
import logging
from typing import Optional
from app.config import settings
from app.models.doctor import Doctor

logger = logging.getLogger(__name__)


class RAGSyncService:
    """Service for syncing doctor data to RAG service."""
    
    def __init__(self):
        """Initialize RAG sync service."""
        self.rag_service_url = settings.RAG_SERVICE_URL
        self.rag_api_key = settings.RAG_SERVICE_API_KEY
    
    def sync_doctor(self, doctor: Doctor) -> bool:
        """
        Sync doctor descriptive data to RAG service.
        Only sends allowed fields - never sends schedule or availability.
        
        Allowed fields:
        - Doctor name
        - Specialization
        - Experience
        - Languages
        - Consultation type
        - General working days (textual)
        - Clinic policies
        
        Args:
            doctor: Doctor model instance
            
        Returns:
            True if sync successful, False otherwise
        """
        if not self.rag_service_url or not self.rag_api_key:
            logger.warning("RAG service not configured, skipping sync")
            return False
        
        try:
            # Prepare payload with ONLY allowed fields
            payload = {
                "doctor_id": str(doctor.id),
                "clinic_id": str(doctor.clinic_id),
                "name": doctor.name,
                "specialization": doctor.specialization,
                "experience_years": doctor.experience_years,
                "languages": doctor.languages,
                "consultation_type": doctor.consultation_type,
                "general_working_days_text": doctor.general_working_days_text,
                # Note: We explicitly DO NOT send:
                # - working_days (specific schedule)
                # - working_hours (specific schedule)
                # - slot_duration_minutes (schedule detail)
                # - appointments (availability)
                # - leaves (availability)
            }
            
            headers = {
                "X-API-Key": self.rag_api_key,
                "Content-Type": "application/json"
            }
            
            # Make HTTP request to RAG service
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.rag_service_url}/doctors/sync",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully synced doctor {doctor.id} to RAG service")
                    return True
                else:
                    logger.error(
                        f"Failed to sync doctor {doctor.id} to RAG service: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error syncing doctor {doctor.id} to RAG service: {str(e)}")
            return False
    
    def delete_doctor(self, doctor_id: str) -> bool:
        """
        Delete doctor from RAG service.
        
        Args:
            doctor_id: UUID of the doctor
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not self.rag_service_url or not self.rag_api_key:
            logger.warning("RAG service not configured, skipping deletion")
            return False
        
        try:
            headers = {
                "X-API-Key": self.rag_api_key,
            }
            
            with httpx.Client(timeout=10.0) as client:
                response = client.delete(
                    f"{self.rag_service_url}/doctors/{doctor_id}",
                    headers=headers
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted doctor {doctor_id} from RAG service")
                    return True
                else:
                    logger.error(
                        f"Failed to delete doctor {doctor_id} from RAG service: "
                        f"Status {response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting doctor {doctor_id} from RAG service: {str(e)}")
            return False
