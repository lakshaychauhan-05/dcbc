"""
Appointment model - represents a booked appointment.
"""
import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration."""
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class AppointmentSource(str, enum.Enum):
    """Appointment source enumeration."""
    AI_CALLING_AGENT = "AI_CALLING_AGENT"
    ADMIN = "ADMIN"


class Appointment(Base):
    """
    Appointment model.
    
    Database is the single source of truth for appointments.
    Google Calendar event_id is stored but never used for booking logic.
    """
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    doctor_email = Column(String(255), ForeignKey("doctors.email", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False, index=True)
    google_calendar_event_id = Column(String(255), nullable=True, unique=True, index=True)
    source = Column(SQLEnum(AppointmentSource), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    
    # Composite index for availability queries
    __table_args__ = (
        Index('idx_appointment_doctor_date_status', 'doctor_email', 'date', 'status'),
    )
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, doctor_email={self.doctor_email}, date={self.date}, status={self.status})>"
