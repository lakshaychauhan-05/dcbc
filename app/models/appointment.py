"""
Appointment model - represents a booked appointment.
"""
import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, Enum as SQLEnum, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration."""
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"


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
    patient_display_name = Column(String(255), nullable=True)  # Name provided at booking time (for display/notifications)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    start_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    end_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False, index=True)
    google_calendar_event_id = Column(String(255), nullable=True, unique=True, index=True)
    calendar_sync_status = Column(String(20), nullable=False, default="PENDING", index=True)
    calendar_sync_attempts = Column(Integer, nullable=False, default=0)
    calendar_sync_next_attempt_at = Column(DateTime(timezone=True), nullable=True, index=True)
    calendar_sync_last_error = Column(String(500), nullable=True)
    source = Column(SQLEnum(AppointmentSource), nullable=False)
    notes = Column(Text, nullable=True)  # Notes for cancellation/reschedule reasons
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    
    # Composite index for availability queries
    __table_args__ = (
        Index('idx_appointment_doctor_date_status', 'doctor_email', 'date', 'status'),
        Index('idx_appointment_doctor_date_start', 'doctor_email', 'date', 'start_time'),
        ExcludeConstraint(
            ("doctor_email", "="),
            (func.tstzrange(start_at_utc, end_at_utc, "[)"), "&&"),  # [) = inclusive start, exclusive end
            name="exclude_overlapping_appointments",
            where=status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        ),
    )
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, doctor_email={self.doctor_email}, date={self.date}, status={self.status})>"
