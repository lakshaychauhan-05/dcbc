# CLAUDE.md

This file provides guidance for Claude Code when working with this codebase.

## Project Overview

Production-ready calendar booking platform with Google Calendar sync, admin/doctor portals, and an AI chatbot for scheduling assistance. Uses a unified architecture with a single backend and single frontend.

## Architecture

### Unified Backend (FastAPI + Python 3.11+)

Single FastAPI application (`app/`) running on port 8000 via `run.py`:

| Route Prefix | Module | Description |
|--------------|--------|-------------|
| `/api/v1/*` | `app/routes/` | Core Calendar API (clinics, doctors, patients, appointments) |
| `/portal/*` | `app/portal/` | Doctor Portal API |
| `/admin/*` | `app/admin/` | Admin Portal API |
| `/chatbot/*` | `app/chatbot/` | Chatbot API (OpenAI) |
| `/health` | `app/main.py` | Health check |

### Unified Frontend (React + Vite + TypeScript)

Single React application (`frontend/`) running on port 5173:

| Route | Description |
|-------|-------------|
| `/` | Chatbot (main page) |
| `/doctor/*` | Doctor Portal |
| `/admin/*` | Admin Portal |

### Database

- PostgreSQL 14+ with SQLAlchemy 2.0 ORM
- Migrations managed via Alembic (`alembic/`)
- Connection pool: size=10, max_overflow=20, timeout=30s, recycle=1800s

## Project Structure

```
.
├── app/                    # Unified Backend
│   ├── admin/              # Admin portal module
│   │   ├── routes/         # Admin API routes
│   │   ├── dependencies.py # Admin auth dependencies
│   │   └── security.py     # Admin JWT handling
│   ├── chatbot/            # Chatbot module
│   │   ├── routes/         # Chatbot API routes
│   │   └── services/       # LLM and chat services
│   ├── portal/             # Doctor portal module
│   │   ├── routes/         # Portal API routes
│   │   ├── dependencies.py # Portal auth dependencies
│   │   └── security.py     # Portal JWT handling
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Core business logic
│   ├── routes/             # Core API routes
│   ├── middleware/         # Request middleware
│   ├── utils/              # Utilities
│   ├── config.py           # Configuration
│   ├── database.py         # Database connection
│   ├── security.py         # Core security
│   └── main.py             # FastAPI application
│
├── frontend/               # Unified Frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   │   ├── admin/      # Admin portal pages
│   │   │   └── doctor/     # Doctor portal pages
│   │   ├── services/       # API services
│   │   ├── hooks/          # Custom hooks
│   │   ├── contexts/       # React contexts
│   │   └── types/          # TypeScript types
│   ├── Dockerfile          # Frontend Docker build
│   └── nginx.conf          # Production nginx config
│
├── alembic/                # Database migrations
├── credentials/            # Google Calendar credentials
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── docs/                   # Documentation
│
├── run.py                  # Application entry point
├── run_migrations.py       # Migration runner
├── Dockerfile              # Backend Docker build
├── docker-compose.yml      # Local development
├── railway.toml            # Railway deployment
└── requirements.txt        # Python dependencies
```

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt           # Backend
cd frontend && npm install                # Frontend

# Database setup
python scripts/create_database.py         # Create database
alembic upgrade head                      # Run migrations
python scripts/populate_sample_data.py    # Seed data (optional)

# Run application
python run.py                             # Backend (port 8000)
cd frontend && npm run dev                # Frontend (port 5173)

# Run tests
pytest                                    # Unit tests
python scripts/test_integration.py        # Integration tests

# Utilities
python scripts/check_db.py                # Check database
python scripts/verify_config.py           # Verify config
python scripts/generate_admin_password.py # Generate admin hash

# Docker
docker-compose up --build -d              # Start all services
```

## Key Files Reference

| Purpose | File |
|---------|------|
| FastAPI app entry | `app/main.py` |
| Configuration | `app/config.py` |
| Database connection | `app/database.py` |
| Core security | `app/security.py` |
| Booking logic | `app/services/booking_service.py` |
| Availability search | `app/services/availability_service.py` |
| Calendar sync | `app/services/calendar_sync_queue.py` |
| Google Calendar | `app/services/google_calendar_service.py` |
| Portal auth | `app/portal/routes/auth.py` |
| Admin auth | `app/admin/routes/auth.py` |
| Chatbot service | `app/chatbot/services/chat_service.py` |
| Frontend API client | `frontend/src/services/api.ts` |

## Authentication

| Endpoint | Method | Header/Token |
|----------|--------|--------------|
| `/api/v1/*` | API Key | `X-API-Key` header |
| `/portal/*` | JWT | `Authorization: Bearer <token>` |
| `/admin/*` | JWT | `Authorization: Bearer <token>` |
| `/chatbot/*` | None | Public |

### Rate Limiting (Core API)

- Algorithm: Fixed-window per minute
- Limit: 120 requests/minute + 30 burst allowance
- Config: `API_KEY_RATE_LIMIT_PER_MINUTE`, `API_KEY_RATE_LIMIT_BURST`

### Idempotency

Use `X-Idempotency-Key` header for safe retries on booking requests.

## Background Workers

Three background workers (threaded, not async):

| Worker | Purpose | Interval |
|--------|---------|----------|
| Calendar Sync Queue | Processes pending sync operations | 5 seconds |
| Calendar Watch Service | Maintains webhook subscriptions | On-demand |
| Calendar Reconcile Service | Backfill sync from Google | 15 minutes |

Disable with `DISABLE_CALENDAR_WORKERS=true`.

## Environment Variables

### Required

```bash
DATABASE_URL                          # PostgreSQL connection
SERVICE_API_KEY                       # Core API authentication
DOCTOR_PORTAL_JWT_SECRET              # Doctor portal JWT
ADMIN_PORTAL_JWT_SECRET               # Admin portal JWT
ADMIN_EMAIL                           # Admin login email
ADMIN_PASSWORD_HASH                   # Admin password (bcrypt)
OPENAI_API_KEY                        # Chatbot AI
CORS_ALLOW_ORIGINS                    # Frontend URL
```

### Optional (Google Calendar)

```bash
DISABLE_CALENDAR_WORKERS=true         # Disable sync (default)
GOOGLE_CALENDAR_CREDENTIALS_PATH      # Service account JSON
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL # Delegation email
WEBHOOK_BASE_URL                      # Public HTTPS URL
GOOGLE_CALENDAR_WEBHOOK_SECRET        # Webhook verification
```

### Optional (OAuth)

```bash
DOCTOR_PORTAL_OAUTH_CLIENT_ID
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET
DOCTOR_PORTAL_OAUTH_REDIRECT_URI
DOCTOR_PORTAL_FRONTEND_CALLBACK_URL
```

See `.env.example` for complete reference.

## Database Migrations

```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback one step
```

## Adding New Features

### New API Endpoint

1. Define Pydantic schema in `app/schemas/`
2. Implement business logic in `app/services/`
3. Create route in `app/routes/` (keep thin, delegate to service)
4. Register router in `app/main.py`

### New Frontend Page

1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Add API calls in `frontend/src/services/api.ts`

## Common Gotchas

- Database URL must use `postgresql+psycopg://` prefix
- Webhooks require public HTTPS URL (use ngrok for local dev)
- Google credentials need domain-wide delegation
- Background workers use threading; avoid async DB calls in threads
- Capture ORM values before starting background threads (session binding)

## Deployment

See `RAILWAY_DEPLOYMENT.md` for Railway deployment guide.

### Quick Deploy

1. Deploy backend from root `/` directory
2. Deploy frontend from `frontend/` directory
3. Set `VITE_API_URL` build arg for frontend
4. Configure environment variables
