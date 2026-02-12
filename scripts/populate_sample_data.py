#!/usr/bin/env python3
"""
Script to populate sample data for development and testing.
Creates sample doctors, patients, and appointments for the chatbot system.
"""
import os
import sys
from datetime import datetime, date, time
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource


def create_sample_doctors(db):
    """Create sample doctors for testing."""
    sample_doctors = [
        {
            "clinic_id": uuid4(),
            "email": "dr.sarah.smith@clinic.com",
            "name": "Dr. Sarah Smith",
            "specialization": "Cardiology",
            "experience_years": 15,
            "languages": ["English", "Spanish"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "09:00", "end": "17:00"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Friday, 9 AM to 5 PM",
            "is_active": True
        },
        {
            "clinic_id": uuid4(),
            "email": "dr.michael.johnson@clinic.com",
            "name": "Dr. Michael Johnson",
            "specialization": "Dermatology",
            "experience_years": 12,
            "languages": ["English", "French"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "08:00", "end": "16:00"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Friday, 8 AM to 4 PM",
            "is_active": True
        },
        {
            "clinic_id": uuid4(),
            "email": "dr.emily.davis@clinic.com",
            "name": "Dr. Emily Davis",
            "specialization": "Pediatrics",
            "experience_years": 8,
            "languages": ["English", "Spanish", "Mandarin"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "09:00", "end": "17:00"},
            "slot_duration_minutes": 25,
            "general_working_days_text": "Monday to Friday, 9 AM to 5 PM",
            "is_active": True
        },
        {
            "clinic_id": uuid4(),
            "email": "dr.robert.wilson@clinic.com",
            "name": "Dr. Robert Wilson",
            "specialization": "Orthopedics",
            "experience_years": 20,
            "languages": ["English"],
            "consultation_type": "In-person",
            "working_days": ["monday", "wednesday", "thursday", "friday"],
            "working_hours": {"start": "10:00", "end": "18:00"},
            "slot_duration_minutes": 45,
            "general_working_days_text": "Monday, Wednesday to Friday, 10 AM to 6 PM",
            "is_active": True
        },
        {
            "clinic_id": uuid4(),
            "email": "dr.lisa.brown@clinic.com",
            "name": "Dr. Lisa Brown",
            "specialization": "Gynecology",
            "experience_years": 14,
            "languages": ["English", "Spanish"],
            "consultation_type": "In-person",
            "working_days": ["monday", "tuesday", "wednesday", "thursday"],
            "working_hours": {"start": "08:30", "end": "16:30"},
            "slot_duration_minutes": 30,
            "general_working_days_text": "Monday to Thursday, 8:30 AM to 4:30 PM",
            "is_active": True
        }
    ]

    created_doctors = []
    for doctor_data in sample_doctors:
        # Check if doctor already exists
        existing = db.query(Doctor).filter(Doctor.email == doctor_data["email"]).first()
        if existing:
            print(f"Doctor {doctor_data['email']} already exists, skipping...")
            continue

        doctor = Doctor(**doctor_data)
        db.add(doctor)
        created_doctors.append(doctor)
        print(f"Created doctor: {doctor.name} ({doctor.specialization})")

    db.commit()
    return created_doctors


def create_sample_patients(db):
    """Create sample patients for testing."""
    sample_patients = [
        {
            "name": "John Doe",
            "mobile_number": "+1234567890",
            "email": "john.doe@email.com",
            "gender": "Male",
            "date_of_birth": date(1985, 5, 15)
        },
        {
            "name": "Jane Smith",
            "mobile_number": "+1234567891",
            "email": "jane.smith@email.com",
            "gender": "Female",
            "date_of_birth": date(1990, 8, 22)
        },
        {
            "name": "Bob Johnson",
            "mobile_number": "+1234567892",
            "email": "bob.johnson@email.com",
            "gender": "Male",
            "date_of_birth": date(1978, 12, 3)
        }
    ]

    created_patients = []
    for patient_data in sample_patients:
        # Check if patient already exists
        existing = db.query(Patient).filter(Patient.mobile_number == patient_data["mobile_number"]).first()
        if existing:
            print(f"Patient {patient_data['mobile_number']} already exists, skipping...")
            created_patients.append(existing)
            continue

        patient = Patient(**patient_data)
        db.add(patient)
        created_patients.append(patient)
        print(f"Created patient: {patient.name}")

    db.commit()
    return created_patients


def create_sample_appointments(db, doctors, patients):
    """Create sample appointments for testing."""
    from datetime import timedelta

    # Create some appointments for the next few days
    base_date = date.today() + timedelta(days=1)  # Tomorrow

    sample_appointments = [
        {
            "doctor": doctors[0],  # Dr. Sarah Smith
            "patient": patients[0],  # John Doe
            "date": base_date,
            "start_time": time(10, 0),
            "end_time": time(10, 30),
            "status": AppointmentStatus.BOOKED,
            "source": AppointmentSource.WEB
        },
        {
            "doctor": doctors[1],  # Dr. Michael Johnson
            "patient": patients[1],  # Jane Smith
            "date": base_date + timedelta(days=1),
            "start_time": time(14, 0),
            "end_time": time(14, 30),
            "status": AppointmentStatus.BOOKED,
            "source": AppointmentSource.WEB
        },
        {
            "doctor": doctors[2],  # Dr. Emily Davis
            "patient": patients[2],  # Bob Johnson
            "date": base_date + timedelta(days=2),
            "start_time": time(11, 0),
            "end_time": time(11, 25),
            "status": AppointmentStatus.BOOKED,
            "source": AppointmentSource.WEB
        }
    ]

    created_appointments = []
    for apt_data in sample_appointments:
        # Check if appointment slot is available (basic check)
        existing = db.query(Appointment).filter(
            Appointment.doctor_email == apt_data["doctor"].email,
            Appointment.date == apt_data["date"],
            Appointment.start_time == apt_data["start_time"],
            Appointment.status == AppointmentStatus.BOOKED
        ).first()

        if existing:
            print(f"Appointment slot already taken for {apt_data['doctor'].name} on {apt_data['date']}, skipping...")
            continue

        appointment = Appointment(
            doctor_email=apt_data["doctor"].email,
            patient_id=apt_data["patient"].id,
            date=apt_data["date"],
            start_time=apt_data["start_time"],
            end_time=apt_data["end_time"],
            status=apt_data["status"],
            source=apt_data["source"]
        )

        db.add(appointment)
        created_appointments.append(appointment)
        print(f"Created appointment: {apt_data['patient'].name} with {apt_data['doctor'].name} on {apt_data['date']}")

    db.commit()
    return created_appointments


def main():
    """Main function to populate sample data."""
    print("Populating sample data for development...")

    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Create sample data
        doctors = create_sample_doctors(db)
        patients = create_sample_patients(db)
        appointments = create_sample_appointments(db, doctors, patients)

        print("\nSample data created successfully!")
        print(f"Doctors: {len(doctors)}")
        print(f"Patients: {len(patients)}")
        print(f"Appointments: {len(appointments)}")

        print("\nSample doctors created:")
        for doctor in doctors:
            print(f"  - {doctor.name} ({doctor.specialization}) - {doctor.email}")

    except Exception as e:
        print(f"Error populating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()