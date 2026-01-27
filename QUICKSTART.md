# Quick Start Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Google Cloud Project with Calendar API enabled
- Service Account with domain-wide delegation

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy env.example to .env
cp env.example .env

# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SERVICE_API_KEY` - Secret API key for authentication
- `GOOGLE_CALENDAR_CREDENTIALS_PATH` - Path to service account JSON
- `GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL` - Admin email for delegation

### 3. Set Up Database

```bash
# Create database
createdb calendar_booking_db

# Run migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Run Application

```bash
# Option 1: Using run.py
python run.py

# Option 2: Using uvicorn directly
uvicorn app.main:app --reload
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing the API

### Create a Doctor

```bash
curl -X POST "http://localhost:8000/api/v1/doctors/" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_id": "00000000-0000-0000-0000-000000000001",
    "name": "Dr. John Doe",
    "email": "dr.john@example.com",
    "specialization": "Cardiology",
    "experience_years": 10,
    "languages": ["English", "Spanish"],
    "consultation_type": "In-person",
    "general_working_days_text": "Monday to Friday",
    "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "working_hours": {"start": "09:00", "end": "17:00"},
    "slot_duration_minutes": 30
  }'
```

### Check Availability

```bash
curl -X GET "http://localhost:8000/api/v1/appointments/availability/{doctor_id}?date=2024-01-15" \
  -H "X-API-Key: your-secret-api-key"
```

### Book Appointment

```bash
curl -X POST "http://localhost:8000/api/v1/appointments/" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "doctor-uuid-here",
    "patient_mobile_number": "+1234567890",
    "patient_name": "Jane Smith",
    "date": "2024-01-15",
    "start_time": "10:00:00",
    "end_time": "10:30:00",
    "source": "AI_CALLING_AGENT"
  }'
```

## Architecture Notes

- **Database is the single source of truth** - All availability calculations come from DB
- **Google Calendar is a mirror** - Events created only after DB commit succeeds
- **RAG is read-only** - Only descriptive doctor data is synced
- **Row-level locking** - Prevents double booking race conditions

## Common Issues

### Database Connection Error
- Verify `DATABASE_URL` is correct
- Ensure PostgreSQL is running
- Check database exists

### Google Calendar API Error
- Verify service account JSON file path
- Check domain-wide delegation is enabled
- Ensure Calendar API is enabled in Google Cloud

### Import Errors
- Ensure you're in the project root directory
- Verify virtual environment is activated
- Check all dependencies are installed
