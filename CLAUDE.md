# CLAUDE.md

This file provides guidance for Claude Code when working with this codebase.

## Project Overview

Multi-service calendar booking platform with Google Calendar sync, admin/doctor portals, and an AI chatbot for scheduling assistance.

## Architecture

### Backend Services (FastAPI + Python 3.11+)
- **Core Calendar API** (`app/`): Main booking logic, runs on port 8000 via `run.py`
- **Admin Portal API** (`admin_portal/`): Admin management, port 5050 via `run_admin_portal.py`
- **Doctor Portal API** (`doctor_portal/`): Doctor scheduling, port 5000 via `run_doctor_portal.py`
- **Chatbot API** (`chatbot-service/`): LLM-powered assistant, port 8002 via `run_chatbot.py`

### Frontend Services (React)
- **Admin UI** (`admin-portal-frontend/`): Vite + React + TypeScript, vanilla CSS, port 5500
- **Doctor UI** (`doctor-portal-frontend/`): Vite + React + TypeScript, Material-UI, port 5173
- **Chatbot UI** (`chatbot-frontend/`): Create React App + TypeScript, Tailwind CSS, port 3000

### Database
- PostgreSQL 14+ with SQLAlchemy 2.0 ORM
- Migrations managed via Alembic (`alembic/`)
- Connection pool: size=10, max_overflow=20, timeout=30s, recycle=1800s

## Common Commands

```bash
# Install Python dependencies (from project root)
pip install -r requirements.txt

# Install chatbot service dependencies
cd chatbot-service && pip install -r requirements.txt

# Install frontend dependencies
cd admin-portal-frontend && npm install
cd doctor-portal-frontend && npm install
cd chatbot-frontend && npm install

# Database setup
python create_database.py               # Create PostgreSQL database
alembic upgrade head                    # Run migrations
python populate_sample_data.py          # Seed test data (optional)

# Run services
python run.py                           # Core Calendar API (8000)
python run_admin_portal.py              # Admin Portal API (5050)
python run_doctor_portal.py             # Doctor Portal API (5000)
cd chatbot-service && python run_chatbot.py  # Chatbot API (8002)

# Run tests
pytest                                  # Backend unit tests (tests/)
python test_integration.py              # Integration tests
cd chatbot-frontend && npm test         # Frontend tests

# Verification & debugging
python verify_config.py                 # Verify environment configuration
python check_db.py                      # Check database connection

# Docker (all services)
docker-compose up --build -d
```

### Windows Development (PowerShell)
```powershell
.\scripts\start_app.ps1                 # Start all services
.\scripts\stop_app.ps1                  # Stop all services
.\scripts\install_all.ps1               # Install all dependencies
.\scripts\verify_setup.ps1              # Verify installation
```

## Code Structure Patterns

### Backend Pattern (FastAPI)
Each backend service follows this layered structure:
```
service/
├── models/      # SQLAlchemy ORM models (database tables)
├── schemas/     # Pydantic v2 request/response validation
├── services/    # Business logic (keep routes thin)
├── routes/      # API endpoint definitions
├── middleware/  # Request processing (e.g., request ID tracing)
├── config.py    # Pydantic settings with env validation
├── security.py  # Auth, rate limiting
└── main.py      # FastAPI app factory, startup/shutdown hooks
```

### Key Files Reference
| Purpose | File |
|---------|------|
| Booking logic | `app/services/booking_service.py` |
| Availability search | `app/services/availability_service.py` |
| Calendar sync | `app/services/calendar_sync_queue.py` |
| Google API wrapper | `app/services/google_calendar_service.py` |
| Main API routes | `app/routes/appointment.py` |
| Configuration | `app/config.py` |
| Database setup | `app/database.py` |

## Background Workers

The Core Calendar API runs three background workers (threaded, not async):

| Worker | Purpose | Interval |
|--------|---------|----------|
| **Calendar Sync Queue** | Processes pending sync operations | 5 seconds |
| **Calendar Watch Service** | Maintains Google Calendar webhook subscriptions | On-demand |
| **Calendar Reconcile Service** | Backfill sync from Google → DB | 15 minutes |

Workers start automatically on app startup and gracefully stop on shutdown. Disable with `DISABLE_CALENDAR_WORKERS=true`.

## Authentication & Security

### API Authentication
| Service | Method | Header/Config |
|---------|--------|---------------|
| Calendar API | API Key | `X-API-Key` header |
| Admin Portal | JWT | `ADMIN_PORTAL_JWT_SECRET` |
| Doctor Portal | Google OAuth + JWT | `DOCTOR_PORTAL_JWT_SECRET` |

### Rate Limiting (Calendar API)
- Algorithm: Fixed-window per minute
- Limit: 120 requests/minute + 30 burst allowance
- Configured via `API_KEY_RATE_LIMIT_PER_MINUTE` and `API_KEY_RATE_LIMIT_BURST`

### Idempotency
Use `X-Idempotency-Key` header for safe retries on booking requests. The system tracks keys to prevent duplicate bookings.

## Google Calendar Integration

### Architecture
- **Database is source of truth**; Google Calendar is a synced mirror
- Each doctor has a distinct Google Calendar
- Sync uses push notifications (webhooks) + periodic reconciliation

### Webhook Flow
1. App registers watch on doctor's calendar via Google API
2. Google sends push notifications to `WEBHOOK_BASE_URL/webhooks/calendar`
3. Webhook handler queues sync job
4. Reconcile service catches any missed changes every 15 minutes

### Required Configuration
```
GOOGLE_CALENDAR_CREDENTIALS_PATH      # Service account JSON file
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL # Domain-wide delegation email
WEBHOOK_BASE_URL                      # Public HTTPS URL for webhooks
GOOGLE_CALENDAR_WEBHOOK_SECRET        # Webhook verification token
```

## Observability

### Logging
- Rotating file logs in `logs/` directory
- Console + file output with configurable levels
- Request ID tracing via `X-Request-ID` header (auto-generated if missing)

### Health Checks
Each service exposes `/health` endpoint checking:
- Database connectivity
- Google credentials validity (Calendar API)
- Background worker status

### API Documentation
Interactive docs at `/docs` endpoint for each service (Swagger UI).

## Environment Variables

### Core Calendar API (root `.env`)
```bash
DATABASE_URL                          # PostgreSQL connection string
SERVICE_API_KEY                       # API key for authentication
GOOGLE_CALENDAR_CREDENTIALS_PATH      # Path to service account JSON
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL # Delegation email
WEBHOOK_BASE_URL                      # Public HTTPS base URL
GOOGLE_CALENDAR_WEBHOOK_SECRET        # Webhook verification
DEFAULT_TIMEZONE                      # Default timezone (e.g., Asia/Kolkata)
CORS_ALLOW_ORIGINS                    # Comma-separated origins
DEBUG                                 # Enable debug mode
DISABLE_CALENDAR_WORKERS              # Disable background sync
MAX_AVAILABILITY_DAYS=30              # Max days for availability search
MAX_AVAILABILITY_RESULTS=200          # Max slots returned
```

### Portal APIs (root `.env`)
```bash
# Admin Portal
ADMIN_PORTAL_PORT=5050
ADMIN_PORTAL_JWT_SECRET
ADMIN_EMAIL
ADMIN_PASSWORD_HASH                   # bcrypt hash
CORE_API_BASE                         # Calendar API URL

# Doctor Portal
DOCTOR_PORTAL_PORT=5000
DOCTOR_PORTAL_JWT_SECRET
DOCTOR_PORTAL_OAUTH_CLIENT_ID
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET
DOCTOR_PORTAL_OAUTH_REDIRECT_URI
DOCTOR_PORTAL_FRONTEND_CALLBACK_URL
```

### Chatbot Service (`chatbot-service/.env`)
```bash
OPENAI_API_KEY                        # OpenAI API key
CALENDAR_SERVICE_URL                  # Calendar API URL
CALENDAR_SERVICE_API_KEY              # API key for calendar
REDIS_URL                             # Optional session storage
PORT=8002
```

See `env.example` for complete reference.

## Testing

### Test Structure
```
tests/
├── test_availability_service.py      # Availability logic
├── test_datetime_utils.py            # DateTime utilities
└── test_idempotency_service.py       # Idempotency handling
```

### Running Tests
```bash
pytest                                # All unit tests
pytest tests/test_availability_service.py  # Specific test file
pytest -v                             # Verbose output
python test_integration.py            # End-to-end tests (requires running services)
```

## Development Notes

### Service Dependencies
- Admin Portal calls → Core Calendar API (`CORE_API_BASE`)
- Chatbot calls → Core Calendar API (`CALENDAR_SERVICE_URL`)
- Doctor Portal uses → Google OAuth + Core Calendar API

### Database Migrations
```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback one step
```

### Adding a New Endpoint
1. Define Pydantic schema in `schemas/`
2. Implement business logic in `services/`
3. Create route in `routes/` (keep it thin, delegate to service)
4. Register router in `main.py`

### Common Gotchas
- Database URL must use `postgresql+psycopg://` (auto-normalized in config)
- Webhooks require public HTTPS URL (use ngrok for local dev)
- Google credentials need domain-wide delegation for calendar access
- Background workers use threading; don't mix with async database calls

## CI/CD & Linting

**Note:** No CI/CD pipeline or linting configuration currently exists. Consider adding:
- GitHub Actions for CI
- Pre-commit hooks
- Python: black, isort, flake8/ruff
- Frontend: ESLint, Prettier
