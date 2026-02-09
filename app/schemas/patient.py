"""
Patient Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
import re


class PatientBase(BaseModel):
    """Base patient schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    mobile_number: str = Field(..., min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    sms_opt_in: bool = Field(default=True, description="Whether patient wants SMS notifications")

    @field_validator("mobile_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        """Normalize phone number to 10 digits or +91XXXXXXXXXX format.

        Accepts:
        - 10 digits: 9876543210
        - With +91: +919876543210
        - With 91 (no plus): 919876543210
        - With leading 0: 09876543210
        - With separators: 987-654-3210, 987 654 3210
        """
        if not value:
            return value
        cleaned = re.sub(r"[^\d+]", "", value)
        if cleaned.startswith("++"):
            cleaned = cleaned[1:]
        has_plus = cleaned.startswith("+")
        digits = re.sub(r"\D", "", cleaned)

        # +91XXXXXXXXXX format (12 digits starting with 91)
        if has_plus and len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"

        # 91XXXXXXXXXX without plus (12 digits starting with 91) - normalize to +91
        if not has_plus and len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"

        # 10-digit number
        if len(digits) == 10:
            return digits

        # 11 digits starting with 0 (leading zero) - strip the 0
        if len(digits) == 11 and digits.startswith("0"):
            return digits[1:]

        raise ValueError("mobile_number must be 10 digits, with optional +91 prefix")


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating patient information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    sms_opt_in: Optional[bool] = Field(None, description="Whether patient wants SMS notifications")


class PatientResponse(PatientBase):
    """Schema for patient response."""
    id: UUID
    sms_opt_in: bool
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
