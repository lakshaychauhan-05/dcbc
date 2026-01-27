"""
Patient medical history model.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class PatientHistory(Base):
    """
    Patient medical history model.
    Stores symptoms, medical conditions, allergies, and notes.
    """
    __tablename__ = "patient_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    symptoms = Column(Text, nullable=True)
    medical_conditions = Column(ARRAY(String), nullable=True, default=list)
    allergies = Column(ARRAY(String), nullable=True, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="history")
    
    def __repr__(self):
        return f"<PatientHistory(id={self.id}, patient_id={self.patient_id})>"
