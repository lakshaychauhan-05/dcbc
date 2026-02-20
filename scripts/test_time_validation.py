"""
Test script to verify past time slot validation.
"""
import sys
from datetime import date, time, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.booking_service import BookingService
from app.services.availability_service import AvailabilityService
from app.schemas.appointment import AppointmentCreate
from app.utils.datetime_utils import now_ist

def test_past_date_validation():
    """Test that bookings for past dates are blocked."""
    print("\n=== Test 1: Past Date Validation ===")
    db = SessionLocal()
    try:
        from app.models.doctor import Doctor
        doctor = db.query(Doctor).filter(Doctor.is_active == True).first()

        if not doctor:
            print("[SKIPPED] No active doctors found in database")
            return

        booking_service = BookingService()

        # Try to book for yesterday
        yesterday = now_ist().date() - timedelta(days=1)
        booking_data = AppointmentCreate(
            doctor_email=doctor.email,
            patient_name="Test Patient",
            patient_mobile_number="9999999999",
            date=yesterday,
            start_time=time(10, 0),
            source="AI_CALLING_AGENT"
        )

        try:
            booking_service.book_appointment(db, booking_data)
            print("[FAILED] Past date booking was allowed")
        except ValueError as e:
            if "cannot be in the past" in str(e):
                print(f"[PASSED] Past date blocked with error: {e}")
            else:
                print(f"[FAILED] Wrong error message: {e}")
    finally:
        db.close()


def test_past_time_validation():
    """Test that bookings for past times on current date are blocked."""
    print("\n=== Test 2: Past Time on Current Date Validation ===")
    db = SessionLocal()
    try:
        from app.models.doctor import Doctor
        doctor = db.query(Doctor).filter(Doctor.is_active == True).first()

        if not doctor:
            print("[SKIPPED] No active doctors found in database")
            return

        booking_service = BookingService()
        current_ist = now_ist()
        current_date = current_ist.date()

        # Try to book for 1 hour ago
        past_time = (current_ist - timedelta(hours=1)).time()
        booking_data = AppointmentCreate(
            doctor_email=doctor.email,
            patient_name="Test Patient",
            patient_mobile_number="9999999999",
            date=current_date,
            start_time=past_time,
            source="AI_CALLING_AGENT"
        )

        try:
            booking_service.book_appointment(db, booking_data)
            print("[FAILED] Past time booking was allowed")
        except ValueError as e:
            if "already passed" in str(e):
                print(f"[PASSED] Past time blocked with error: {e}")
            else:
                print(f"[FAILED] Wrong error message: {e}")
    finally:
        db.close()


def test_availability_excludes_past_times():
    """Test that availability endpoint excludes past time slots for today."""
    print("\n=== Test 3: Availability Excludes Past Times ===")
    db = SessionLocal()
    try:
        availability_service = AvailabilityService()
        current_ist = now_ist()
        current_date = current_ist.date()
        current_time = current_ist.time()

        # Get availability for a doctor on today
        # This should not include any slots before current time
        try:
            from app.models.doctor import Doctor
            doctor = db.query(Doctor).filter(Doctor.is_active == True).first()

            if not doctor:
                print("[SKIPPED] No active doctors found in database")
                return

            availability = availability_service.get_available_slots(
                db=db,
                doctor_email=doctor.email,
                target_date=current_date
            )

            # Check if any available slot is in the past
            past_slots = [slot for slot in availability.available_slots
                         if slot.start_time <= current_time]

            if past_slots:
                print(f"[FAILED] Found {len(past_slots)} past time slots in availability:")
                for slot in past_slots[:3]:  # Show first 3
                    print(f"   - {slot.start_time} (current time: {current_time})")
            else:
                print(f"[PASSED] No past time slots in availability (current time: {current_time})")
                if availability.available_slots:
                    first_slot = availability.available_slots[0]
                    print(f"   First available slot: {first_slot.start_time}")

        except ValueError as e:
            print(f"[NOTE] {e}")
    finally:
        db.close()


def test_future_booking_allowed():
    """Test that future bookings are still allowed."""
    print("\n=== Test 4: Future Booking Allowed ===")
    print("[NOTE] This test requires a valid doctor and available slot")
    print("   Skipping to avoid actual booking. Manual verification recommended.")


if __name__ == "__main__":
    print("=" * 60)
    print("Time Validation Test Suite")
    print("=" * 60)
    print(f"Current IST Time: {now_ist()}")

    test_past_date_validation()
    test_past_time_validation()
    test_availability_excludes_past_times()
    test_future_booking_allowed()

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
