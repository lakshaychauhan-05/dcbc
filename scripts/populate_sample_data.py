#!/usr/bin/env python3
"""
Script to populate sample data for development and testing.
Creates sample clinics, doctors, patients, and appointments.

Usage:
    python scripts/populate_sample_data.py

Safe to run multiple times — skips records that already exist.
"""
import os
import sys
from datetime import datetime, date, time, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource
from app.utils.datetime_utils import to_utc


def create_sample_clinics(db):
    """Create sample clinics."""
    sample_clinics = [
        {
            "name": "Legacy Clinic 1",
            "address": "123 Main Street, New Delhi",
            "phone_number": "+911234567890",
            "email": "contact@legacyclinic1.com",
            "timezone": "Asia/Kolkata",
            "is_active": True,
        },
        {
            "name": "HealthFirst Medical Center",
            "address": "456 Park Avenue, Mumbai",
            "phone_number": "+919876543210",
            "email": "info@healthfirst.com",
            "timezone": "Asia/Kolkata",
            "is_active": True,
        },
    ]

    created = []
    for clinic_data in sample_clinics:
        existing = db.query(Clinic).filter(Clinic.name == clinic_data["name"]).first()
        if existing:
            print(f"  Clinic '{clinic_data['name']}' already exists, skipping")
            created.append(existing)
            continue

        clinic = Clinic(**clinic_data)
        db.add(clinic)
        db.flush()
        created.append(clinic)
        print(f"  + Created clinic: {clinic.name}")

    db.commit()
    return created


def create_sample_doctors(db, clinics):
    """Create sample doctors linked to existing clinics."""
    clinic_1 = clinics[0]  # Legacy Clinic 1
    clinic_2 = clinics[1] if len(clinics) > 1 else clinics[0]

    sample_doctors = [
        {
            "email": "dr.sarah.smith@clinic.com",
            "name": "Dr. Sarah Smith",
            "clinic_id": clinic_1.id,
            "specialization": "Cardiology",
            "experience_years": 15,
            "languages": ["English", "Hindi"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "09:00", "end": "17:00"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Friday, 9 AM to 5 PM",
            "is_active": True,
        },
        {
            "email": "dr.michael.johnson@clinic.com",
            "name": "Dr. Michael Johnson",
            "clinic_id": clinic_1.id,
            "specialization": "Dermatology",
            "experience_years": 12,
            "languages": ["English", "Hindi"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "08:00", "end": "16:00"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Friday, 8 AM to 4 PM",
            "is_active": True,
        },
        {
            "email": "dr.emily.davis@clinic.com",
            "name": "Dr. Emily Davis",
            "clinic_id": clinic_2.id,
            "specialization": "Pediatrics",
            "experience_years": 8,
            "languages": ["English", "Hindi", "Marathi"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "09:00", "end": "17:00"},
            "slot_duration_minutes": 25,
            "general_working_days_text": "Monday to Friday, 9 AM to 5 PM",
            "is_active": True,
        },
        {
            "email": "dr.robert.wilson@clinic.com",
            "name": "Dr. Robert Wilson",
            "clinic_id": clinic_2.id,
            "specialization": "Orthopedics",
            "experience_years": 20,
            "languages": ["English"],
            "consultation_type": "In-person",
            "working_days": ["monday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "10:00", "end": "18:00"},
            "slot_duration_minutes": 45,
            "general_working_days_text": "Mon, Wed-Fri, 10 AM to 6 PM",
            "is_active": True,
        },
        {
            "email": "dr.lisa.brown@clinic.com",
            "name": "Dr. Lisa Brown",
            "clinic_id": clinic_1.id,
            "specialization": "Gynecology",
            "experience_years": 14,
            "languages": ["English", "Hindi"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday"],
            "working_hours": {"start": "08:30", "end": "16:30"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Thursday, 8:30 AM to 4:30 PM",
            "is_active": True,
        },
    ]

    created = []
    for doctor_data in sample_doctors:
        existing = db.query(Doctor).filter(Doctor.email == doctor_data["email"]).first()
        if existing:
            print(f"  Doctor '{doctor_data['email']}' already exists, skipping")
            created.append(existing)
            continue

        doctor = Doctor(**doctor_data)
        db.add(doctor)
        created.append(doctor)
        print(f"  + Created doctor: {doctor.name} ({doctor.specialization})")

    db.commit()
    return created


def create_sample_patients(db):
    """Create sample patients."""
    sample_patients = [
        {
            "name": "Rahul Sharma",
            "mobile_number": "+919999900001",
            "email": "rahul.sharma@email.com",
            "gender": "Male",
            "date_of_birth": date(1985, 5, 15),
        },
        {
            "name": "Priya Patel",
            "mobile_number": "+919999900002",
            "email": "priya.patel@email.com",
            "gender": "Female",
            "date_of_birth": date(1990, 8, 22),
        },
        {
            "name": "Amit Kumar",
            "mobile_number": "+919999900003",
            "email": "amit.kumar@email.com",
            "gender": "Male",
            "date_of_birth": date(1978, 12, 3),
        },
    ]

    created = []
    for patient_data in sample_patients:
        existing = db.query(Patient).filter(
            Patient.mobile_number == patient_data["mobile_number"]
        ).first()
        if existing:
            print(f"  Patient '{patient_data['mobile_number']}' already exists, skipping")
            created.append(existing)
            continue

        patient = Patient(**patient_data)
        db.add(patient)
        db.flush()
        created.append(patient)
        print(f"  + Created patient: {patient.name}")

    db.commit()
    return created


def _build_appointment(doctor_email, patient_id, patient_name, apt_date, start, end):
    """Helper to build an appointment dict with computed UTC times."""
    tz = "Asia/Kolkata"
    return {
        "doctor_email": doctor_email,
        "patient_id": patient_id,
        "patient_display_name": patient_name,
        "date": apt_date,
        "start_time": start,
        "end_time": end,
        "timezone": tz,
        "start_at_utc": to_utc(apt_date, start, tz),
        "end_at_utc": to_utc(apt_date, end, tz),
        "status": AppointmentStatus.BOOKED,
        "source": AppointmentSource.ADMIN,
        "calendar_sync_status": "SYNCED",
    }


def create_sample_appointments(db, doctors, patients):
    """Create a few sample appointments for the next few days."""
    if not doctors or not patients:
        print("  No doctors or patients available, skipping appointments")
        return []

    tomorrow = date.today() + timedelta(days=1)

    appointments_data = []
    if len(doctors) >= 1 and len(patients) >= 1:
        appointments_data.append(_build_appointment(
            doctors[0].email, patients[0].id, patients[0].name,
            tomorrow, time(10, 0), time(10, 30),
        ))
    if len(doctors) >= 2 and len(patients) >= 2:
        appointments_data.append(_build_appointment(
            doctors[1].email, patients[1].id, patients[1].name,
            tomorrow + timedelta(days=1), time(14, 0), time(14, 30),
        ))
    if len(doctors) >= 3 and len(patients) >= 3:
        appointments_data.append(_build_appointment(
            doctors[2].email, patients[2].id, patients[2].name,
            tomorrow + timedelta(days=2), time(11, 0), time(11, 25),
        ))

    created = []
    for apt_data in appointments_data:
        existing = db.query(Appointment).filter(
            Appointment.doctor_email == apt_data["doctor_email"],
            Appointment.date == apt_data["date"],
            Appointment.start_time == apt_data["start_time"],
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
        ).first()

        if existing:
            print(f"  Appointment slot already taken on {apt_data['date']}, skipping")
            continue

        appointment = Appointment(**apt_data)
        db.add(appointment)
        created.append(appointment)
        print(f"  + Created appointment: {apt_data['patient_display_name']} with {apt_data['doctor_email']} on {apt_data['date']}")

    db.commit()
    return created


def main():
    """Populate sample data for development."""
    print("=" * 55)
    print("  Populating Sample Data")
    print("=" * 55)

    db = SessionLocal()
    try:
        print("\n[1/4] Creating clinics...")
        clinics = create_sample_clinics(db)

        print("\n[2/4] Creating doctors...")
        doctors = create_sample_doctors(db, clinics)

        print("\n[3/4] Creating patients...")
        patients = create_sample_patients(db)

        print("\n[4/4] Creating sample appointments...")
        appointments = create_sample_appointments(db, doctors, patients)

        print("\n" + "-" * 55)
        print("  Summary")
        print("-" * 55)
        print(f"  Clinics     : {len(clinics)}")
        print(f"  Doctors     : {len(doctors)}")
        print(f"  Patients    : {len(patients)}")
        print(f"  Appointments: {len(appointments)}")

        print("\n  Sample doctors created:")
        for doctor in doctors:
            print(f"    - {doctor.name} ({doctor.specialization}) [{doctor.email}]")

        print("\n" + "=" * 55)
        print("  Done! Sample data is ready.")
        print("=" * 55)

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
