"""
Clinic Pydantic schemas for admin-facing CRUD.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClinicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    timezone: str = Field(default="UTC", max_length=64)
    address: Optional[str] = Field(None, max_length=512)
    is_active: bool = True


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(None, max_length=64)
    address: Optional[str] = Field(None, max_length=512)
    is_active: Optional[bool] = None


class ClinicResponse(ClinicBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClinicListResponse(BaseModel):
    clinics: list[ClinicResponse]
    total: int
