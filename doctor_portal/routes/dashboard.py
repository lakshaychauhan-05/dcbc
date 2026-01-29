"""
Dashboard and data access routes for the doctor portal.
"""
from datetime import date, datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from doctor_portal.dependencies import get_current_doctor_account, get_portal_db
from doctor_portal.schemas import (
    DoctorProfile,
    AppointmentItem,
    AppointmentsResponse,
    PatientSummary,
    PatientsResponse,
    PatientDetail,
    PatientHistoryItem,
    OverviewResponse,
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.patient_history import PatientHistory

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/me", response_model=DoctorProfile)
def get_me(account=Depends(get_current_doctor_account)) -> DoctorProfile:
    doctor = account.doctor
    return DoctorProfile.model_validate(doctor)


def _appointment_to_item(appt: Appointment, patient: Patient) -> AppointmentItem:
    return AppointmentItem(
        id=str(appt.id),
        date=appt.date,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        timezone=appt.timezone,
        patient=PatientSummary(
            id=str(patient.id),
            name=patient.name,
            mobile_number=patient.mobile_number,
            email=patient.email,
        ),
    )


@router.get("/appointments", response_model=AppointmentsResponse)
def list_appointments(
    start_date: date | None = None,
    end_date: date | None = None,
    status_filter: AppointmentStatus | None = None,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> AppointmentsResponse:
    query = (
        db.query(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(Appointment.doctor_email == account.doctor_email)
    )

    if start_date:
        query = query.filter(Appointment.date >= start_date)
    if end_date:
        query = query.filter(Appointment.date <= end_date)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    rows = query.order_by(Appointment.date, Appointment.start_time).all()
    items = [_appointment_to_item(appt, patient) for appt, patient in rows]
    return AppointmentsResponse(appointments=items)


@router.get("/patients", response_model=PatientsResponse)
def list_patients(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientsResponse:
    patients = (
        db.query(Patient)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .filter(Appointment.doctor_email == account.doctor_email)
        .distinct(Patient.id)
        .all()
    )
    summaries = [
        PatientSummary(
            id=str(p.id),
            name=p.name,
            mobile_number=p.mobile_number,
            email=p.email,
        )
        for p in patients
    ]
    return PatientsResponse(patients=summaries)


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient_detail(
    patient_id: UUID,
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> PatientDetail:
    # Ensure the doctor has at least one appointment with this patient
    has_access = (
        db.query(Appointment.id)
        .filter(Appointment.doctor_email == account.doctor_email, Appointment.patient_id == patient_id)
        .first()
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found for this doctor",
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    history = (
        db.query(PatientHistory)
        .filter(PatientHistory.patient_id == patient_id)
        .order_by(PatientHistory.created_at.desc())
        .all()
    )

    history_items = [
        PatientHistoryItem.model_validate(item) for item in history
    ]

    return PatientDetail(
        id=str(patient.id),
        name=patient.name,
        mobile_number=patient.mobile_number,
        email=patient.email,
        gender=patient.gender,
        date_of_birth=patient.date_of_birth,
        history=history_items,
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    db: Session = Depends(get_portal_db),
    account=Depends(get_current_doctor_account),
) -> OverviewResponse:
    today = datetime.now(timezone.utc).date()
    upcoming_query = (
        db.query(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(
            Appointment.doctor_email == account.doctor_email,
            Appointment.date >= today,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
        )
        .order_by(Appointment.date, Appointment.start_time)
        .limit(20)
    )
    rows = upcoming_query.all()
    upcoming = [_appointment_to_item(appt, patient) for appt, patient in rows]

    doctor_profile = DoctorProfile.model_validate(account.doctor)
    return OverviewResponse(doctor=doctor_profile, upcoming_appointments=upcoming)
