"""
Patient Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


class PatientBase(BaseModel):
    """Base patient schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    mobile_number: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating patient information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None


class PatientResponse(PatientBase):
    """Schema for patient response."""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class PatientHistoryCreate(BaseModel):
    """Schema for creating patient history."""
    symptoms: Optional[str] = None
    medical_conditions: Optional[List[str]] = Field(default_factory=list)
    allergies: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class PatientHistoryResponse(PatientHistoryCreate):
    """Schema for patient history response."""
    id: UUID
    patient_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
