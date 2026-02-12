#!/usr/bin/env python3
"""
Script to reset a doctor's portal password.
"""
import sys
from app.database import SessionLocal
from app.models.doctor_account import DoctorAccount
from doctor_portal.security import get_password_hash

def reset_doctor_password(doctor_email: str, new_password: str):
    """Reset password for a specific doctor."""
    db = SessionLocal()
    try:
        account = db.query(DoctorAccount).filter(
            DoctorAccount.doctor_email == doctor_email.lower()
        ).first()

        if not account:
            print(f"❌ No account found for {doctor_email}")
            print("\nAvailable doctor accounts:")
            accounts = db.query(DoctorAccount).all()
            for acc in accounts:
                print(f"  - {acc.doctor_email}")
            return False

        account.password_hash = get_password_hash(new_password)
        db.commit()
        print(f"✅ Password reset successfully for {doctor_email}")
        print(f"   New password: {new_password}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_doctor_password.py <doctor_email> <new_password>")
        print("\nExample:")
        print('  python reset_doctor_password.py "dr.sarah.smith@clinic.com" "NewPass@123"')
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    reset_doctor_password(email, password)
