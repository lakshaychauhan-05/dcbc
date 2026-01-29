"""
Clinic management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.security import verify_api_key
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.schemas.clinic import (
    ClinicCreate,
    ClinicUpdate,
    ClinicResponse,
    ClinicListResponse,
)

router = APIRouter()


@router.post("/", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    clinic_data: ClinicCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Create a new clinic.
    """
    existing = db.query(Clinic).filter(Clinic.name == clinic_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clinic with name '{clinic_data.name}' already exists",
        )

    clinic = Clinic(**clinic_data.model_dump())
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic


@router.get("/", response_model=ClinicListResponse)
async def list_clinics(
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    List clinics with optional active filter and pagination.
    """
    from app.config import settings

    if skip < 0 or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip must be >= 0 and limit must be >= 1",
        )
    if limit > settings.MAX_LIST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"limit must be <= {settings.MAX_LIST_LIMIT}",
        )

    query = db.query(Clinic)
    if is_active is not None:
        query = query.filter(Clinic.is_active == is_active)

    total = query.count()
    clinics = query.offset(skip).limit(limit).all()
    return ClinicListResponse(clinics=clinics, total=total)


@router.get("/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(
    clinic_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )
    return clinic


@router.put("/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    clinic_id: UUID,
    clinic_data: ClinicUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    if clinic_data.name and clinic_data.name != clinic.name:
        name_conflict = db.query(Clinic).filter(Clinic.name == clinic_data.name).first()
        if name_conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Clinic with name '{clinic_data.name}' already exists",
            )

    for field, value in clinic_data.model_dump(exclude_unset=True).items():
        setattr(clinic, field, value)

    db.commit()
    db.refresh(clinic)
    return clinic


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic(
    clinic_id: UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Delete a clinic.
    If doctors exist and force is False, block deletion to avoid accidental cascade.
    """
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    if not force:
        has_doctors = db.query(Doctor).filter(Doctor.clinic_id == clinic_id).first()
        if has_doctors:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Clinic has doctors; use force=true to cascade delete",
            )

    db.delete(clinic)
    db.commit()
    return None
