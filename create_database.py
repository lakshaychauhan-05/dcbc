#!/usr/bin/env python3
"""
Script to create the PostgreSQL database for the Calendar Booking project.
This script should be run before running migrations.
"""
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os
from getpass import getpass

def create_database():
    """Create the calendar_booking_db database."""
    
    # Database configuration
    db_name = "calendar_booking_db"
    db_user ="calendar"
    db_password = "calendar123"
    db_host = "localhost"
    db_port = "5432"
    
    # Get password from user
    print("=" * 50)
    print("PostgreSQL Database Creation Script")
    print("=" * 50)
    print()
    print(f"This script will create the database: {db_name}")
    print()
    
    # Ask for PostgreSQL password
    db_password = getpass(f"Enter password for PostgreSQL user '{db_user}': ")
    
    if not db_password:
        print("\n❌ Error: Password cannot be empty")
        sys.exit(1)
    
    print("\n🔄 Connecting to PostgreSQL...")
    
    try:
        # Connect to PostgreSQL server (connect to default 'postgres' database)
        conn = psycopg2.connect(
            dbname='postgres',
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        # Set autocommit mode
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL successfully!")
        
        # Check if database already exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"\n⚠️  Database '{db_name}' already exists!")
            response = input("Do you want to drop and recreate it? (yes/no): ").lower()
            
            if response == 'yes':
                print(f"\n🗑️  Dropping existing database '{db_name}'...")
                cursor.execute(sql.SQL("DROP DATABASE {}").format(
                    sql.Identifier(db_name)
                ))
                print(f"✅ Database '{db_name}' dropped successfully!")
            else:
                print("\n✅ Using existing database. You can proceed with migrations.")
                cursor.close()
                conn.close()
                return True
        
        # Create the database
        print(f"\n🔨 Creating database '{db_name}'...")
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(db_name)
        ))
        print(f"✅ Database '{db_name}' created successfully!")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ Setup Complete!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Verify your .env file has the correct DATABASE_URL")
        print(f"   DATABASE_URL=postgresql://{db_user}:YOUR_PASSWORD@{db_host}:{db_port}/{db_name}")
        print("\n2. Run database migrations:")
        print("   alembic upgrade head")
        print("\n3. Start the application:")
        print("   python run.py")
        print()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Error: Could not connect to PostgreSQL")
        print(f"Details: {e}")
        print("\nPossible issues:")
        print("  1. PostgreSQL service is not running")
        print("  2. Incorrect password")
        print("  3. PostgreSQL is not installed or not in PATH")
        print("\nTo check PostgreSQL service:")
        print('  Get-Service -Name postgresql*  (in PowerShell)')
        return False
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
