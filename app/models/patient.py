"""
Patient model - represents a patient.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Date, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Patient(Base):
    """
    Patient model.
    Mobile number is unique and indexed for quick lookup.
    """
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    mobile_number = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    history = relationship("PatientHistory", back_populates="patient", cascade="all, delete-orphan")
    
    # Index on mobile_number for faster lookups
    __table_args__ = (
        Index('idx_patient_mobile', 'mobile_number'),
    )
    
    def __repr__(self):
        return f"<Patient(id={self.id}, name={self.name}, mobile={self.mobile_number})>"
