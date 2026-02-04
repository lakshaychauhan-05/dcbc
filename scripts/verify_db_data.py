#!/usr/bin/env python3
"""
Verify clinics and doctors data in the database.
Uses the same DATABASE_URL and models as the core API (run.py).
Run from project root: python verify_db_data.py
"""
import os
import sys

# Ensure project root is on path and .env is loaded from project root
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

def main():
    from sqlalchemy import text
    from app.database import SessionLocal
    from app.models.clinic import Clinic
    from app.models.doctor import Doctor
    from app.config import settings

    print("Using DATABASE_URL (host/db only):", _mask_url(settings.DATABASE_URL))
    print()

    db = SessionLocal()
    try:
        # Check which tables exist
        r_clinics = db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'clinics')"
        ))
        r_doctors = db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'doctors')"
        ))
        clinics_exist = r_clinics.scalar()
        doctors_exist = r_doctors.scalar()

        clinic_count = 0
        doctor_count = 0

        # Clinics
        if not clinics_exist:
            print("Clinics: table 'clinics' does NOT exist.")
            print("  -> Run migrations: alembic upgrade head")
        else:
            clinic_count = db.query(Clinic).count()
            clinics = db.query(Clinic).limit(10).all()
            print(f"Clinics: total = {clinic_count}")
            if clinics:
                for c in clinics:
                    print(f"  - id={c.id} name={c.name!r} is_active={c.is_active}")
            else:
                print("  (no rows)")
        print()

        # Doctors (check independently; doctors table can exist even if clinics was missing earlier)
        if not doctors_exist:
            print("Doctors: table 'doctors' does NOT exist.")
            print("  -> Run migrations: alembic upgrade head")
        else:
            try:
                doctor_count = db.query(Doctor).count()
                doctors = db.query(Doctor).limit(10).all()
                print(f"Doctors: total = {doctor_count}")
                if doctors:
                    for d in doctors:
                        print(f"  - email={d.email!r} name={d.name!r} clinic_id={d.clinic_id} is_active={d.is_active}")
                else:
                    print("  (no rows)")
            except Exception as e:
                # Fallback: raw SQL in case ORM fails (e.g. schema mismatch)
                try:
                    r = db.execute(text("SELECT COUNT(*) FROM doctors"))
                    doctor_count = r.scalar() or 0
                    print(f"Doctors: total = {doctor_count} (raw count; ORM failed: {e})")
                    if doctor_count:
                        rows = db.execute(text(
                            "SELECT email, name, clinic_id, is_active FROM doctors LIMIT 10"
                        )).fetchall()
                        for row in rows:
                            print(f"  - email={row[0]!r} name={row[1]!r} clinic_id={row[2]} is_active={row[3]}")
                except Exception as e2:
                    print("Doctors: error:", e2)
        print()

        if not clinics_exist or not doctors_exist:
            print("Apply migrations if needed: alembic upgrade head")
        elif clinic_count == 0 and doctor_count == 0:
            print("No clinics or doctors in DB. Create them via admin portal or API.")
        else:
            print("Data is present. If admin UI shows empty, check: core API running, SERVICE_API_KEY match, limit<=200.")
    finally:
        db.close()


def _mask_url(url: str) -> str:
    """Show only scheme, host, port, and path (no password)."""
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        netloc = p.hostname or ""
        if p.port:
            netloc += f":{p.port}"
        return urlunparse((p.scheme, netloc, p.path or "/", "", "", ""))
    except Exception:
        return "(parse error)"


if __name__ == "__main__":
    main()
