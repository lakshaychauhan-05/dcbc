"""
Doctor leave model - represents doctor holidays/leaves.
"""
import uuid
from datetime import date
from sqlalchemy import Column, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class DoctorLeave(Base):
    """
    Doctor leave model.
    Stores doctor holidays and leaves that affect availability.
    """
    __tablename__ = "doctor_leaves"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    doctor_email = Column(String(255), ForeignKey("doctors.email", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    reason = Column(String(500), nullable=True)

    # Relationships
    doctor = relationship("Doctor", back_populates="leaves")

    # Ensure one leave record per doctor per date
    __table_args__ = (
        UniqueConstraint('doctor_email', 'date', name='uq_doctor_leave_date'),
    )
    
    def __repr__(self):
        return f"<DoctorLeave(id={self.id}, doctor_email={self.doctor_email}, date={self.date})>"
