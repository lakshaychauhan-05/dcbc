#!/usr/bin/env python3
"""
Script to run database migrations using Alembic.
"""
import subprocess
import sys
import os

def run_migrations():
    """Run Alembic migrations."""
    
    print("=" * 50)
    print("Database Migration Script")
    print("=" * 50)
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("ERROR: .env file not found!")
        print("Please create .env file from env.example")
        return False

    print("Found .env file")

    # Check if alembic.ini exists
    if not os.path.exists('alembic.ini'):
        print("ERROR: alembic.ini not found!")
        return False

    print("Found alembic.ini")
    print()
    
    try:
        # Run alembic upgrade head
        print("Running database migrations...")
        print("-" * 50)
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print("-" * 50)
            print("\nMigrations completed successfully!")
            print("\nNext step:")
            print("  python run.py")
            print()
            return True
        else:
            print("\nMigration failed!")
            print("\nTroubleshooting:")
            print("  1. Verify DATABASE_URL in .env is correct")
            print("  2. Ensure database exists: python create_database.py")
            print("  3. Check PostgreSQL is running")
            return False

    except FileNotFoundError:
        print("\nERROR: Alembic not found!")
        print("Please install dependencies: pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"\nERROR running migrations: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
