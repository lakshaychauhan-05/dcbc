# Calendar Booking Platform

A production-ready calendar booking system with Google Calendar sync, admin/doctor portals, and an AI chatbot for scheduling assistance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                   │
│                        Port: 5173                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Chatbot   │  │   Doctor    │  │    Admin    │          │
│  │   (Home)    │  │   Portal    │  │   Portal    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│                      Port: 8000                              │
│                                                              │
│  /api/v1/*      → Core Calendar API                         │
│  /portal/*      → Doctor Portal API                         │
│  /admin/*       → Admin Portal API                          │
│  /chatbot/*     → Chatbot API (OpenAI)                      │
│  /health        → Health Check                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  PostgreSQL  │
                   └──────────────┘
```

## Project Structure

```
.
├── app/                    # Unified Backend (FastAPI)
│   ├── admin/              # Admin portal module
│   ├── chatbot/            # Chatbot module (OpenAI)
│   ├── portal/             # Doctor portal module
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic
│   ├── routes/             # Core API routes
│   ├── middleware/         # Request middleware
│   ├── utils/              # Utilities
│   ├── config.py           # Configuration
│   ├── database.py         # Database connection
│   ├── security.py         # Authentication
│   └── main.py             # FastAPI application
│
├── frontend/               # Unified Frontend (React + Vite)
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   │   ├── admin/      # Admin portal pages
│   │   │   └── doctor/     # Doctor portal pages
│   │   ├── services/       # API services
│   │   ├── hooks/          # Custom React hooks
│   │   ├── contexts/       # React contexts
│   │   └── types/          # TypeScript types
│   ├── Dockerfile          # Frontend Docker build
│   └── nginx.conf          # Nginx configuration
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
├── docker-compose.yml      # Local development setup
├── railway.toml            # Railway deployment config
├── requirements.txt        # Python dependencies
└── .env.example            # Environment template
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+
- OpenAI API key (for chatbot)
- Google Cloud service account (optional, for calendar sync)

## Quick Start

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone https://github.com/lakshaychauhan-05/dcbc.git
cd dcbc

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, SERVICE_API_KEY, OPENAI_API_KEY
# Required: ADMIN_EMAIL, ADMIN_PASSWORD_HASH, JWT secrets
```

### 3. Setup Database

```bash
# Create database
python scripts/create_database.py

# Run migrations
alembic upgrade head

# (Optional) Populate sample data
python scripts/populate_sample_data.py
```

### 4. Run Application

```bash
# Terminal 1: Start backend
python run.py

# Terminal 2: Start frontend
cd frontend && npm run dev
```

Access the application:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Docker Deployment

```bash
# Build and run all services
docker-compose up --build -d

# Access:
# - Frontend: http://localhost:5173
# - Backend: http://localhost:8000
```

## API Endpoints

| Prefix | Description | Authentication |
|--------|-------------|----------------|
| `/api/v1/*` | Core Calendar API | X-API-Key header |
| `/portal/*` | Doctor Portal | JWT (Bearer token) |
| `/admin/*` | Admin Portal | JWT (Bearer token) |
| `/chatbot/*` | Chatbot API | None (public) |
| `/health` | Health check | None |

## Frontend Routes

| Route | Description |
|-------|-------------|
| `/` | Chatbot (main page) |
| `/doctor/login` | Doctor login |
| `/doctor/dashboard` | Doctor dashboard |
| `/doctor/appointments` | Appointments management |
| `/doctor/patients` | Patient records |
| `/admin/login` | Admin login |
| `/admin/dashboard` | Admin dashboard |
| `/admin/clinics` | Clinic management |
| `/admin/doctors` | Doctor management |

## Environment Variables

### Required

```bash
# Database
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/calendar_booking

# Authentication
SERVICE_API_KEY=your-api-key
DOCTOR_PORTAL_JWT_SECRET=your-doctor-jwt-secret
ADMIN_PORTAL_JWT_SECRET=your-admin-jwt-secret
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=$2b$12$...  # bcrypt hash

# Chatbot
OPENAI_API_KEY=sk-...
```

### Optional

```bash
# Google Calendar (disabled by default)
DISABLE_CALENDAR_WORKERS=true
GOOGLE_CALENDAR_CREDENTIALS_PATH=
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=

# SMS Notifications (disabled by default)
SMS_NOTIFICATIONS_ENABLED=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# OAuth (for Google login)
DOCTOR_PORTAL_OAUTH_CLIENT_ID=
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET=
```

See `.env.example` for full configuration reference.

## Scripts

| Script | Description |
|--------|-------------|
| `python run.py` | Start backend server |
| `python run_migrations.py` | Run database migrations |
| `python scripts/create_database.py` | Create PostgreSQL database |
| `python scripts/populate_sample_data.py` | Seed sample data |
| `python scripts/generate_admin_password.py` | Generate admin password hash |
| `python scripts/check_db.py` | Verify database connection |
| `python scripts/verify_config.py` | Validate configuration |

## Testing

```bash
# Run backend tests
pytest

# Run integration tests
python scripts/test_integration.py
```

## Deployment

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for Railway deployment guide.

### Quick Railway Setup

1. Create PostgreSQL database on Railway
2. Deploy backend from root directory
3. Deploy frontend from `frontend/` directory
4. Configure environment variables

## License

MIT
