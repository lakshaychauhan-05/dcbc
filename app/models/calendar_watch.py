"""
CalendarWatch model - tracks Google Calendar push notification channels.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CalendarWatch(Base):
    """
    Tracks active Google Calendar watch channels.
    Stores channel info for webhook processing.
    """
    __tablename__ = "calendar_watches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    doctor_email = Column(String(255), ForeignKey("doctors.email", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(String(255), unique=True, nullable=False, index=True)
    resource_id = Column(String(255), nullable=False)
    expiration = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    doctor = relationship("Doctor", backref="calendar_watches")
    
    def __repr__(self):
        return f"<CalendarWatch(doctor_email={self.doctor_email}, channel_id={self.channel_id})>"
