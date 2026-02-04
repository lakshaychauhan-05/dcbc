# Calendar Booking Platform

Multi-service calendar booking system with Google Calendar sync, admin/doctor portals, and an AI chatbot for scheduling assistance.

## Repository Layout
```
.
├── app/                     # Core Calendar API (FastAPI)
│   ├── models/, schemas/, services/, routes/
│   └── run.py               # Entry for calendar service
├── admin_portal/            # Admin portal API (FastAPI)
├── doctor_portal/           # Doctor portal API (FastAPI)
├── chatbot-service/         # Chatbot API (FastAPI + LLM)
│   └── run_chatbot.py
├── admin-portal-frontend/   # Admin UI (Vite + React, port 5500)
├── doctor-portal-frontend/  # Doctor UI (Vite + React, port 5173)
├── chatbot-frontend/        # Chatbot UI (CRA, port 3000)
├── alembic/                 # DB migrations
├── env.example              # Root env template (shared backends)
├── docker-compose.yml       # Optional containerized stack
├── start_project.ps1        # Windows launcher (all services)
├── start_all_services.sh    # Docker Compose launcher
└── tests/                   # Pytest suite
```

## Services & Default Ports
- Calendar API (core): `run.py` → 8000
- Doctor Portal API: `run_doctor_portal.py` → 5000
- Admin Portal API: `run_admin_portal.py` → 5050
- Chatbot API: `chatbot-service/run_chatbot.py` → defaults to 8002 (Docker publishes 8001)
- Frontends: chatbot UI 3000, doctor UI 5173, admin UI 5500

## Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+ (local) or Docker
- Google Cloud service account for Calendar API

## Environment Configuration
1) Backends: copy `env.example` → `.env` and fill:
- `DATABASE_URL`, `SERVICE_API_KEY`, `GOOGLE_CALENDAR_*`, `WEBHOOK_BASE_URL`
- Portal auth: `DOCTOR_PORTAL_*`, `ADMIN_PORTAL_*`, `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH`
- Upstream URLs: `CORE_API_BASE`, `PORTAL_API_BASE`

2) Frontends:
- `admin-portal-frontend/.env.example` → `.env` (`VITE_ADMIN_API_URL`)
- `doctor-portal-frontend/.env.example` → `.env` (`VITE_PORTAL_API_URL`)

3) Chatbot service:
- `chatbot-service/env.example` → `.env` (set `OPENAI_API_KEY`, `CALENDAR_SERVICE_API_KEY`, `PORT`)

## Install Dependencies
```bash
# Python (root services)
python -m venv venv
.\venv\Scripts\activate           # Windows
pip install -r requirements.txt

# Chatbot API
cd chatbot-service
pip install -r requirements.txt

# Frontends
cd admin-portal-frontend  && npm install
cd ../doctor-portal-frontend && npm install
cd ../chatbot-frontend && npm install
```

## Database
```bash
# Create database
createdb calendar_booking_db

# Apply migrations
alembic upgrade head
```

## Running Locally (manual)
```bash
# Core calendar API
python run.py

# Admin portal API
python run_admin_portal.py

# Doctor portal API
python run_doctor_portal.py

# Chatbot API
cd chatbot-service && python run_chatbot.py
```
Frontends (in their folders):
```bash
npm run dev -- --host --port 5500   # admin UI
npm run dev -- --host --port 5173   # doctor UI
npm start                            # chatbot UI (CRA)
```
Windows convenience launcher (starts all backends + frontends in separate terminals):
```bash
pwsh ./start_project.ps1
```

## Docker Compose
```bash
cp chatbot-service/env.example chatbot-service/.env   # add OPENAI_API_KEY
docker-compose up --build -d
```
Exposes: calendar API 8000, chatbot API 8001, chatbot UI 3000, Postgres 5432, Redis 6379.

## API Docs & Health
- Calendar API: `http://localhost:8000/docs` (health: `/health`)
- Admin Portal API: `http://localhost:5050/docs`
- Doctor Portal API: `http://localhost:5000/docs`
- Chatbot API: `http://localhost:{PORT}/docs`

## Authentication
- Calendar API: `X-API-Key` header (`SERVICE_API_KEY` / `SERVICE_API_KEYS`)
- Portals: JWT-based auth with secrets in `.env`; Google OAuth configured via `DOCTOR_PORTAL_OAUTH_*`
- Webhooks: `GOOGLE_CALENDAR_WEBHOOK_SECRET` used to verify inbound calls

## Google Calendar Notes
- Database is the source of truth; Calendar is mirrored after DB commits.
- Webhooks require a public HTTPS `WEBHOOK_BASE_URL`.
- Each doctor owns a distinct Google Calendar; credentials live at `GOOGLE_CALENDAR_CREDENTIALS_PATH`.

## Data & Sample Utilities
- `create_database.py` / `check_db.py` / `populate_sample_data.py` / `export_doctor_data.py`
- `run_migrations.py` to apply Alembic migrations programmatically.

## Testing
```bash
pytest                              # unit tests
python scripts/test_integration.py  # integration tests
```
Frontends:
```bash
cd chatbot-frontend && npm test
```

## Production Tips
- Use HTTPS, rotate API keys, and set strict CORS.
- Configure connection pooling and backups for PostgreSQL.
- Monitor calendar sync workers (`CALENDAR_SYNC_*`, `CALENDAR_RECONCILE_*`) and webhook health.
- Set `DEBUG=False` and provide strong `ADMIN_PASSWORD_HASH`/JWT secrets before deploying.
