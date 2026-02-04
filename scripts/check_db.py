#!/usr/bin/env python3
"""
Script to check database status and data
"""
import psycopg2

def check_database():
    try:
        # Connect to postgres database
        conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='postgres123',
            host='localhost',
            port='5432'
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if calendar_booking_db exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'calendar_booking_db';")
        exists = cursor.fetchone()

        if exists:
            print('✅ Database calendar_booking_db exists')

            # Connect to the database and check tables
            cursor.close()
            conn.close()

            conn = psycopg2.connect(
                dbname='calendar_booking_db',
                user='postgres',
                password='postgres123',
                host='localhost',
                port='5432'
            )
            cursor = conn.cursor()

            # Check tables
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
            tables = cursor.fetchall()
            print('Tables in database:', [t[0] for t in tables])

            # Check data in key tables
            cursor.execute('SELECT COUNT(*) FROM doctors;')
            doctor_count = cursor.fetchone()[0]
            print(f'Doctors in database: {doctor_count}')

            cursor.execute('SELECT COUNT(*) FROM patients;')
            patient_count = cursor.fetchone()[0]
            print(f'Patients in database: {patient_count}')

            cursor.execute('SELECT COUNT(*) FROM appointments;')
            appointment_count = cursor.fetchone()[0]
            print(f'Appointments in database: {appointment_count}')

        else:
            print('❌ Database calendar_booking_db does not exist')
            print('Need to recreate the database')

        cursor.close()
        conn.close()

    except Exception as e:
        print(f'❌ Database connection error: {e}')

if __name__ == "__main__":
    check_database()