"""
Appointment Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID
from app.models.appointment import AppointmentStatus, AppointmentSource


class AppointmentBase(BaseModel):
    """Base appointment schema with common fields."""
    doctor_id: UUID
    patient_id: UUID
    date: date
    start_time: time
    end_time: time
    source: AppointmentSource


class AppointmentCreate(BaseModel):
    """Schema for creating a new appointment."""
    doctor_email: str  # Changed to email (unique identifier)
    patient_mobile_number: str = Field(..., min_length=10, max_length=20)
    patient_name: str = Field(..., min_length=1, max_length=255)
    patient_email: Optional[str] = None
    patient_gender: Optional[str] = None
    patient_date_of_birth: Optional[date] = None
    date: date
    start_time: time
    source: AppointmentSource = AppointmentSource.AI_CALLING_AGENT
    # Patient history
    symptoms: Optional[str] = None
    medical_conditions: Optional[list[str]] = Field(default_factory=list)
    allergies: Optional[list[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling an appointment."""
    new_date: date
    new_start_time: time
    new_end_time: time


class AppointmentResponse(BaseModel):
    """Schema for appointment response."""
    id: UUID
    doctor_email: str  # Changed from doctor_id: UUID to doctor_email: str
    patient_id: UUID
    date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    google_calendar_event_id: Optional[str] = None
    source: AppointmentSource
    created_at: datetime
    
    class Config:
        from_attributes = True


class AvailabilitySlot(BaseModel):
    """Schema for available time slot."""
    start_time: time
    end_time: time


class AvailabilityResponse(BaseModel):
    """Schema for availability response."""
    doctor_id: str  # Changed from UUID to str (email identifier)
    date: date
    available_slots: list[AvailabilitySlot]
    total_slots: int
