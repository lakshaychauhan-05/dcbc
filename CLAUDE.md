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
- **Admin UI** (`admin-portal-frontend/`): Vite + React, port 5500
- **Doctor UI** (`doctor-portal-frontend/`): Vite + React, port 5173
- **Chatbot UI** (`chatbot-frontend/`): Create React App, port 3000

### Database
- PostgreSQL 14+ with SQLAlchemy ORM
- Migrations managed via Alembic (`alembic/`)

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

# Database migrations
alembic upgrade head

# Run services
python run.py                           # Core Calendar API (8000)
python run_admin_portal.py              # Admin Portal API (5050)
python run_doctor_portal.py             # Doctor Portal API (5000)
cd chatbot-service && python run_chatbot.py  # Chatbot API (8002)

# Run tests
pytest                                  # Backend tests
python test_integration.py              # Integration tests
cd chatbot-frontend && npm test         # Frontend tests

# Docker (all services)
docker-compose up --build -d
```

## Code Structure Patterns

### Backend Pattern (FastAPI)
Each backend service follows this structure:
- `models/` - SQLAlchemy models
- `schemas/` - Pydantic request/response schemas
- `services/` - Business logic layer
- `routes/` - API endpoint definitions

### Authentication
- Calendar API: `X-API-Key` header
- Portals: JWT-based auth
- Google OAuth for doctor portal

### Key Environment Variables
See `env.example` for full list. Critical ones:
- `DATABASE_URL` - PostgreSQL connection string
- `SERVICE_API_KEY` - Internal API authentication
- `GOOGLE_CALENDAR_*` - Google Calendar integration
- `OPENAI_API_KEY` - Chatbot LLM (in chatbot-service/.env)

## Important Notes

- Database is source of truth; Google Calendar is synced mirror
- Each doctor has a distinct Google Calendar
- Webhooks require public HTTPS `WEBHOOK_BASE_URL`
- API docs available at `/docs` endpoint for each service
