"""
Doctor Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class DoctorBase(BaseModel):
    """Base doctor schema with common fields."""
    clinic_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr  # Google Calendar email
    phone_number: Optional[str] = Field(None, max_length=20, description="Doctor's mobile for SMS notifications")
    specialization: str = Field(..., min_length=1, max_length=255)
    experience_years: int = Field(..., ge=0)
    languages: List[str] = Field(default_factory=list)
    consultation_type: str = Field(..., min_length=1, max_length=100)
    general_working_days_text: Optional[str] = Field(None, max_length=500)
    working_days: List[str] = Field(..., min_items=1)  # e.g., ["monday", "tuesday"]
    working_hours: dict = Field(..., description="Working hours with start and end times")  # {"start": "09:00", "end": "17:00"}
    slot_duration_minutes: int = Field(default=30, ge=5, le=120)
    timezone: str = Field(default="UTC", max_length=64)


class DoctorCreate(DoctorBase):
    """Schema for creating a new doctor."""
    pass


class DoctorUpdate(BaseModel):
    """Schema for updating doctor information."""
    clinic_id: Optional[UUID] = Field(None, description="Reassign doctor to another clinic")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20, description="Doctor's mobile for SMS notifications")
    specialization: Optional[str] = Field(None, min_length=1, max_length=255)
    experience_years: Optional[int] = Field(None, ge=0)
    languages: Optional[List[str]] = None
    consultation_type: Optional[str] = Field(None, min_length=1, max_length=100)
    general_working_days_text: Optional[str] = Field(None, max_length=500)
    working_days: Optional[List[str]] = Field(None, min_items=1)
    working_hours: Optional[dict] = None
    slot_duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    timezone: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class DoctorResponse(DoctorBase):
    """Schema for doctor response."""
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DoctorListResponse(BaseModel):
    """Schema for listing doctors."""
    doctors: List[DoctorResponse]
    total: int
