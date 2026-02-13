"""
Pydantic schemas for the doctor portal.
"""
from datetime import datetime, date, time
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from app.models.appointment import AppointmentStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class DoctorProfile(BaseModel):
    email: EmailStr
    name: str
    specialization: str
    experience_years: int
    languages: List[str]
    consultation_type: str
    timezone: str
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    id: str
    name: str
    mobile_number: str | None = None
    email: str | None = None
    sms_opt_in: bool = True


class PatientHistoryItem(BaseModel):
    id: str
    created_at: datetime
    symptoms: Optional[str] = None
    medical_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Convert UUID to string for id field
        if hasattr(obj, 'id') and hasattr(obj.id, 'hex'):
            obj_dict = {
                'id': str(obj.id),
                'created_at': obj.created_at,
                'symptoms': obj.symptoms,
                'medical_conditions': obj.medical_conditions,
                'allergies': obj.allergies,
                'notes': obj.notes,
            }
            return super().model_validate(obj_dict, **kwargs)
        return super().model_validate(obj, **kwargs)


class PatientDetail(PatientSummary):
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    history: List[PatientHistoryItem] = Field(default_factory=list)


class AppointmentItem(BaseModel):
    id: str
    date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    timezone: str
    patient: PatientSummary
    notes: Optional[str] = None
    source: Optional[str] = None
    calendar_sync_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AppointmentsResponse(BaseModel):
    appointments: List[AppointmentItem]


class PatientsResponse(BaseModel):
    patients: List[PatientSummary]


class OverviewResponse(BaseModel):
    doctor: DoctorProfile
    upcoming_appointments: List[AppointmentItem]


# ============== SCHEMAS FOR CRUD OPERATIONS ==============

class RescheduleRequest(BaseModel):
    """Request to reschedule an appointment."""
    new_date: date
    new_start_time: time
    new_end_time: time
    reason: Optional[str] = None

    @field_validator('new_date')
    @classmethod
    def validate_date_not_in_past(cls, v: date) -> date:
        from app.utils.datetime_utils import now_ist
        today = now_ist().date()
        if v < today:
            raise ValueError('Cannot reschedule to a past date')
        return v

    @model_validator(mode='after')
    def validate_time_range(self):
        if self.new_end_time <= self.new_start_time:
            raise ValueError('End time must be after start time')
        return self


class CancelRequest(BaseModel):
    """Request to cancel an appointment."""
    reason: Optional[str] = None


class CompleteRequest(BaseModel):
    """Request to mark appointment as completed."""
    notes: Optional[str] = None


class AddPatientHistoryRequest(BaseModel):
    """Request to add patient history entry."""
    symptoms: Optional[str] = None
    medical_conditions: Optional[List[str]] = Field(default_factory=list)
    allergies: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class UpdatePatientHistoryRequest(BaseModel):
    """Request to update patient history entry."""
    symptoms: Optional[str] = None
    medical_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None


class UpdatePatientRequest(BaseModel):
    """Request to update patient info."""
    name: Optional[str] = None
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None


class UpdateProfileRequest(BaseModel):
    """Request to update doctor profile."""
    name: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    languages: Optional[List[str]] = None
    consultation_type: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Request to change password."""
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True
