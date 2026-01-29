"""
Pydantic schemas for the doctor portal.
"""
from datetime import datetime, date, time
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
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

    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    id: str
    name: str
    mobile_number: str | None = None
    email: str | None = None


class PatientHistoryItem(BaseModel):
    id: str
    created_at: datetime
    symptoms: Optional[str] = None
    medical_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class AppointmentsResponse(BaseModel):
    appointments: List[AppointmentItem]


class PatientsResponse(BaseModel):
    patients: List[PatientSummary]


class OverviewResponse(BaseModel):
    doctor: DoctorProfile
    upcoming_appointments: List[AppointmentItem]
