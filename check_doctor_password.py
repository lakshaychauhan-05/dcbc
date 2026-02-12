#!/usr/bin/env python3
"""
Script to verify if a password works for a doctor account.
"""
import sys
from app.database import SessionLocal
from app.models.doctor_account import DoctorAccount
from doctor_portal.security import verify_password

def check_doctor_password(doctor_email: str, test_password: str = None):
    """Check if a password works for a doctor account."""
    db = SessionLocal()
    try:
        account = db.query(DoctorAccount).filter(
            DoctorAccount.doctor_email == doctor_email.lower()
        ).first()

        if not account:
            print(f"[ERROR] No account found for {doctor_email}")
            print("\nAvailable doctor accounts:")
            accounts = db.query(DoctorAccount).all()
            for acc in accounts:
                print(f"  - {acc.doctor_email}")
            return

        print(f"[SUCCESS] Account found for {doctor_email}")
        print(f"   Active: {account.is_active}")
        print(f"   Last login: {account.last_login_at or 'Never'}")
        print(f"   Password hash exists: {'Yes' if account.password_hash else 'No'}")

        if test_password:
            print(f"\n[TESTING] Checking password...")
            if verify_password(test_password, account.password_hash):
                print(f"[SUCCESS] Password '{test_password}' is CORRECT!")
            else:
                print(f"[FAILED] Password '{test_password}' is INCORRECT")
        else:
            print("\n[INFO] To test a password, provide it as the second argument:")
            print(f'   python check_doctor_password.py "{doctor_email}" "your_password"')

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_doctor_password.py <doctor_email> [password_to_test]")
        print("\nExamples:")
        print('  python check_doctor_password.py "lakshaychauhan05@gmail.com"')
        print('  python check_doctor_password.py "lakshaychauhan05@gmail.com" "testpass@123"')
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None
    check_doctor_password(email, password)
