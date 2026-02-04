#!/usr/bin/env python3
"""
Utility script to generate a bcrypt hash for the admin password.
Run this script and copy the output hash to your .env file.

Usage:
    python generate_admin_password.py
    # or
    python generate_admin_password.py "your-password-here"
"""
import sys
import getpass

try:
    from passlib.context import CryptContext
except ImportError:
    print("Error: passlib is not installed.")
    print("Install it with: pip install passlib[bcrypt]")
    sys.exit(1)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_hash(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    return pwd_context.hash(password)


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        print("Admin Password Generator")
        print("=" * 40)
        password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm admin password: ")

        if password != confirm:
            print("\nError: Passwords do not match!")
            sys.exit(1)

        if len(password) < 6:
            print("\nError: Password must be at least 6 characters!")
            sys.exit(1)

    hash_value = generate_hash(password)

    print("\n" + "=" * 40)
    print("Generated bcrypt hash:")
    print(hash_value)
    print("=" * 40)
    print("\nCopy this hash to your .env file:")
    print(f"ADMIN_PASSWORD_HASH={hash_value}")
    print()


if __name__ == "__main__":
    main()
