"""
Doctor model - represents a doctor in the clinic.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class Doctor(Base):
    """
    Doctor model.

    Email serves as the unique identifier for each doctor.
    Each doctor has their own Google Calendar email ID.
    Multiple doctors can exist under a single clinic.
    """
    __tablename__ = "doctors"

    # Email as primary key (unique identifier)
    email = Column(String(255), primary_key=True, index=True)  # Primary key and unique identifier

    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(13), nullable=True)  # 10 digits with optional +91 prefix
    specialization = Column(String(255), nullable=False)
    experience_years = Column(Integer, nullable=False)
    languages = Column(ARRAY(String), nullable=False, default=list)
    consultation_type = Column(String(100), nullable=False)
    general_working_days_text = Column(String(500), nullable=True)  # For RAG
    working_days = Column(JSON, nullable=False)  # e.g., ["monday", "tuesday", "wednesday"]
    working_hours = Column(JSON, nullable=False)  # e.g., {"start": "09:00", "end": "17:00"}
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")
    leaves = relationship("DoctorLeave", back_populates="doctor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Doctor(email={self.email}, name={self.name})>"
