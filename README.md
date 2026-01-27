# Calendar & Appointment Booking Microservice

A production-ready Calendar & Appointment Booking microservice built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and Google Calendar integration.

## Architecture Overview

### Critical Architecture Rules

1. **Database is the SINGLE SOURCE OF TRUTH**
   - All availability calculations come from the database
   - All booking logic relies on database state
   - Google Calendar is only a mirror of confirmed appointments

2. **Google Calendar Integration**
   - Google Calendar events are created/updated ONLY AFTER DB transaction succeeds
   - Never read availability from Google Calendar
   - Never trust Google Calendar for booking logic
   - Each doctor has their own Google Calendar email ID

3. **RAG Integration**
   - RAG is strictly READ-ONLY
   - Stores ONLY descriptive doctor data (name, specialization, experience, etc.)
   - Never stores schedule, slots, availability, or appointments
   - Used only for answering patient questions and doctor discovery

4. **Multi-Doctor Support**
   - Multiple doctors exist under a single clinic
   - Each doctor has independent working hours and schedules

## Tech Stack

- **Python 3.11**
- **FastAPI** - Modern, fast web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **Google Calendar API** - Calendar event synchronization
- **python-dotenv** - Environment variable management

## Project Structure

```
calendar-service/
│
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection and session
│   ├── security.py             # API key authentication
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── doctor.py
│   │   ├── patient.py
│   │   ├── patient_history.py
│   │   ├── appointment.py
│   │   └── doctor_leave.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── doctor.py
│   │   ├── patient.py
│   │   └── appointment.py
│   │
│   ├── services/               # Business logic services
│   │   ├── availability_service.py
│   │   ├── booking_service.py
│   │   ├── google_calendar_service.py
│   │   └── rag_sync_service.py
│   │
│   └── routes/                 # API routes
│       ├── doctor.py
│       ├── patient.py
│       └── appointment.py
│
├── alembic/                    # Database migrations
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Database Models

### Doctor
- `id` (UUID, primary key)
- `clinic_id` (UUID)
- `name` (String)
- `email` (String, unique) - Google Calendar email
- `specialization` (String)
- `experience_years` (Integer)
- `languages` (Array)
- `consultation_type` (String)
- `general_working_days_text` (String) - For RAG
- `working_days` (JSON) - e.g., ["monday", "tuesday"]
- `working_hours` (JSON) - {"start": "09:00", "end": "17:00"}
- `slot_duration_minutes` (Integer)
- `is_active` (Boolean)
- `created_at`, `updated_at` (DateTime)

### Patient
- `id` (UUID, primary key)
- `name` (String)
- `mobile_number` (String, unique, indexed)
- `email` (String, optional)
- `gender` (String, optional)
- `date_of_birth` (Date, optional)
- `created_at` (DateTime)

### PatientHistory
- `id` (UUID, primary key)
- `patient_id` (UUID, foreign key)
- `symptoms` (Text)
- `medical_conditions` (Array)
- `allergies` (Array)
- `notes` (Text)
- `created_at` (DateTime)

### Appointment
- `id` (UUID, primary key)
- `doctor_id` (UUID, foreign key)
- `patient_id` (UUID, foreign key)
- `date` (Date)
- `start_time` (Time)
- `end_time` (Time)
- `status` (Enum: BOOKED, CANCELLED, RESCHEDULED)
- `google_calendar_event_id` (String, optional)
- `source` (Enum: AI_CALLING_AGENT, ADMIN)
- `created_at` (DateTime)

### DoctorLeave
- `id` (UUID, primary key)
- `doctor_id` (UUID, foreign key)
- `date` (Date)
- `reason` (String, optional)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd calendar-service
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `env.example` to `.env` and update the values:

```bash
# On Linux/Mac
cp env.example .env

# On Windows
copy env.example .env
```

Edit `.env` with your configuration:
- `DATABASE_URL` - PostgreSQL connection string
- `SERVICE_API_KEY` - Secret API key for service authentication
- `GOOGLE_CALENDAR_CREDENTIALS_PATH` - Path to Google service account JSON
- `GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL` - Admin email for domain-wide delegation
- `RAG_SERVICE_URL` - RAG service URL (optional)
- `RAG_SERVICE_API_KEY` - RAG service API key (optional)

### 5. Set Up Google Calendar API

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create a Service Account
4. Download service account JSON credentials
5. Enable domain-wide delegation for the service account
6. Place the JSON file at the path specified in `GOOGLE_CALENDAR_CREDENTIALS_PATH`

### 6. Set Up Database

Create a PostgreSQL database:

```bash
createdb calendar_booking_db
```

### 7. Run Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 8. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Doctor Management

- `POST /api/v1/doctors/` - Create doctor
- `GET /api/v1/doctors/{doctor_id}` - Get doctor by ID
- `GET /api/v1/doctors/` - List doctors (with filters)
- `PUT /api/v1/doctors/{doctor_id}` - Update doctor
- `POST /api/v1/doctors/{doctor_id}/leaves` - Add doctor leave
- `DELETE /api/v1/doctors/{doctor_id}/leaves/{leave_id}` - Delete doctor leave

### Patient Management

- `POST /api/v1/patients/` - Create patient
- `GET /api/v1/patients/{patient_id}` - Get patient by ID
- `GET /api/v1/patients/mobile/{mobile_number}` - Get patient by mobile
- `PUT /api/v1/patients/{patient_id}` - Update patient
- `POST /api/v1/patients/{patient_id}/history` - Add patient history
- `GET /api/v1/patients/{patient_id}/history` - Get patient history

### Appointment Management

- `GET /api/v1/appointments/availability/{doctor_id}` - Get available slots
- `POST /api/v1/appointments/` - Book appointment
- `GET /api/v1/appointments/{appointment_id}` - Get appointment
- `GET /api/v1/appointments/doctor/{doctor_id}` - Get doctor appointments
- `GET /api/v1/appointments/patient/{patient_id}` - Get patient appointments
- `PUT /api/v1/appointments/{appointment_id}/reschedule` - Reschedule appointment
- `DELETE /api/v1/appointments/{appointment_id}` - Cancel appointment

## Authentication

All endpoints require API key authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:8000/api/v1/doctors/
```

## Key Features

### Availability Calculation

- Calculates available slots based on:
  - Doctor working hours (from database)
  - Slot duration (from database)
  - Booked appointments (from database)
  - Doctor leaves (from database)
- Never reads from Google Calendar

### Appointment Booking

- Validates slot availability from database
- Creates patient if not exists (based on mobile number)
- Uses database transactions with row-level locking to prevent double booking
- Creates Google Calendar event AFTER database commit succeeds
- Stores Google Calendar event ID for future updates

### Rescheduling

- Validates new slot availability
- Updates appointment in database transaction
- Updates Google Calendar event accordingly

### Cancellation

- Marks appointment as cancelled in database
- Deletes Google Calendar event

### RAG Sync

- Automatically syncs doctor descriptive data to RAG service
- Only sends allowed fields (name, specialization, experience, etc.)
- Never sends schedule, slots, or availability data
- Triggered on doctor create/update

## Error Handling

The service includes comprehensive error handling:
- Validation errors return 400 Bad Request
- Not found errors return 404 Not Found
- Authentication errors return 401 Unauthorized
- Server errors return 500 Internal Server Error
- All errors are logged for debugging

## Database Transactions

- All booking operations use database transactions
- Row-level locking prevents double booking
- Google Calendar operations happen AFTER database commit
- Rollback on any database errors

## Logging

The service uses Python's logging module. Configure logging levels in your environment or application configuration.

## Production Considerations

1. **Security**
   - Use strong API keys
   - Enable HTTPS
   - Configure CORS appropriately
   - Use environment variables for secrets

2. **Database**
   - Use connection pooling
   - Set up database backups
   - Monitor database performance

3. **Google Calendar**
   - Handle API rate limits
   - Implement retry logic for failed calendar operations
   - Monitor calendar sync status

4. **Monitoring**
   - Set up application monitoring
   - Monitor API response times
   - Track error rates
   - Monitor database performance

5. **Scaling**
   - Use load balancer for multiple instances
   - Configure database read replicas if needed
   - Implement caching for frequently accessed data

