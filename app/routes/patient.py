"""
Patient management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.security import verify_api_key
from app.models.patient import Patient
from app.models.patient_history import PatientHistory
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientHistoryCreate,
    PatientHistoryResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create a new patient."""
    try:
        # Check if mobile number already exists
        existing = db.query(Patient).filter(
            Patient.mobile_number == patient_data.mobile_number
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with mobile number {patient_data.mobile_number} already exists"
            )
        
        patient = Patient(**patient_data.model_dump())
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create patient: {str(e)}"
        )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get patient by ID."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    return patient


@router.get("/mobile/{mobile_number}", response_model=PatientResponse)
async def get_patient_by_mobile(
    mobile_number: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get patient by mobile number."""
    patient = db.query(Patient).filter(Patient.mobile_number == mobile_number).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with mobile number {mobile_number} not found"
        )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update patient information."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    try:
        update_data = patient_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)
        
        db.commit()
        db.refresh(patient)
        
        return patient
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patient: {str(e)}"
        )


@router.post("/{patient_id}/history", response_model=PatientHistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_patient_history(
    patient_id: UUID,
    history_data: PatientHistoryCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Add patient medical history."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    try:
        patient_history = PatientHistory(
            patient_id=patient_id,
            **history_data.model_dump()
        )
        
        db.add(patient_history)
        db.commit()
        db.refresh(patient_history)
        
        return patient_history
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding patient history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add patient history: {str(e)}"
        )


@router.get("/{patient_id}/history", response_model=List[PatientHistoryResponse])
async def get_patient_history(
    patient_id: UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get patient medical history."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    history = db.query(PatientHistory).filter(
        PatientHistory.patient_id == patient_id
    ).order_by(PatientHistory.created_at.desc()).all()
    
    return history
