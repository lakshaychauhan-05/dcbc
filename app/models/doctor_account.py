"""
Doctor account credentials for portal authentication.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class DoctorAccount(Base):
    """
    Portal authentication account for a doctor.

    Uses doctor_email as a unique reference to the doctor profile.
    """
    __tablename__ = "doctor_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    doctor_email = Column(String(255), ForeignKey("doctors.email", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DoctorAccount(doctor_email={self.doctor_email}, active={self.is_active})>"
