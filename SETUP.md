# Calendar Booking Platform — Local Setup Guide

> **Stack:** Python 3.11 · FastAPI · PostgreSQL 14 · React 18 · Vite · TypeScript · Tailwind CSS

---

## Prerequisites

Install the following before proceeding:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11 or higher | https://www.python.org/downloads |
| Node.js | 18 or higher | https://nodejs.org |
| PostgreSQL | 14 or higher | https://www.postgresql.org/download |
| Git | Any | https://git-scm.com |

Verify your installations:

```bash
python --version      # Python 3.11.x
node --version        # v18.x.x or higher
npm --version         # 9.x.x or higher
psql --version        # psql (PostgreSQL) 14.x or higher
git --version         # git version 2.x.x
```

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/lakshaychauhan-05/dcbc.git
cd dcbc
```

---

## Step 2 — Database Setup

### 2.1 — Create the database

Open a PostgreSQL shell:

```bash
# Linux / macOS
psql -U postgres

# Windows (run from PostgreSQL bin directory or use pgAdmin)
psql -U postgres
```

Run the following SQL commands:

```sql
CREATE DATABASE calendar_booking;
\q
```

### 2.2 — Verify the database exists

```bash
psql -U postgres -c "\l" | grep calendar_booking
```

You should see `calendar_booking` listed.

---

## Step 3 — Backend Setup

### 3.1 — Create and activate a virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate — Linux / macOS
source venv/bin/activate

# Activate — Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate — Windows (Command Prompt)
venv\Scripts\activate.bat
```

Your terminal prompt should now show `(venv)` at the start.

### 3.2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, Alembic, OpenAI, Passlib, and all other backend dependencies.

### 3.3 — Configure environment variables

Copy the example environment file:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

### 3.4 — Generate secrets

You need to generate values for three fields.

**Generate JWT secrets** (run this command twice — once for each secret):

```bash
# Linux / macOS
openssl rand -hex 32

# Windows (PowerShell) — if openssl is not available
python -c "import secrets; print(secrets.token_hex(32))"
```

**Generate the admin password hash** (replace `YourPassword` with your chosen admin password):

```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourPassword'))"
```

Copy the output — it will look like `$2b$12$...`

### 3.5 — Edit the `.env` file

Open `.env` in any text editor and fill in these required fields:

```env
# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PG_PASSWORD@localhost:5432/calendar_booking

# ── API Security ──────────────────────────────────────────────────────────────
SERVICE_API_KEY=any-random-string-min-16-chars

# ── Doctor Portal ─────────────────────────────────────────────────────────────
DOCTOR_PORTAL_JWT_SECRET=<first-hex-string-from-step-3.4>

# ── Admin Portal ──────────────────────────────────────────────────────────────
ADMIN_PORTAL_JWT_SECRET=<second-hex-string-from-step-3.4>
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD_HASH=<bcrypt-hash-from-step-3.4>

# ── Chatbot ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-your-openai-api-key

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ORIGINS=http://localhost:5173
```

> All other fields in `.env` have defaults and are optional for local development.

### 3.6 — Run database migrations

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, initial schema
INFO  [alembic.runtime.migration] Running upgrade xxxx -> yyyy, ...
```

### 3.7 — Start the backend server

```bash
python run.py
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The backend is now running at **http://localhost:8000**

---

## Step 4 — Frontend Setup

Open a **new terminal window** (keep the backend running in the first one).

### 4.1 — Navigate to the frontend directory

```bash
cd frontend
```

### 4.2 — Install Node.js dependencies

```bash
npm install
```

### 4.3 — Create the frontend environment file

```bash
# Linux / macOS
echo "VITE_API_URL=http://localhost:8000" > .env

# Windows (PowerShell)
Set-Content .env "VITE_API_URL=http://localhost:8000"
```

### 4.4 — Start the frontend development server

```bash
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

The frontend is now running at **http://localhost:5173**

---

## Step 5 — Admin Account & First-Time Data

### 5.1 — Log in to the Admin Portal

1. Open **http://localhost:5173/admin/login** in your browser
2. Enter your `ADMIN_EMAIL` and the **plain-text password** you used in Step 3.4
3. You will be redirected to the admin dashboard

### 5.2 — Create a clinic

1. Go to **Admin → Clinics → Add Clinic**
2. Fill in the clinic name, address, phone, and email
3. Click **Create**

### 5.3 — Create a doctor

1. Go to **Admin → Doctors → Add Doctor**
2. Fill in all doctor details and assign the clinic created above
3. Click **Create**

The chatbot and booking system are now fully operational.

---

## Step 6 — Verify the Setup

Run these checks to confirm everything is working:

```bash
# 1. Backend health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","timestamp":"..."}


# 2. List clinics (replace with your SERVICE_API_KEY from .env)
curl http://localhost:8000/api/v1/clinics \
  -H "X-API-Key: your-SERVICE_API_KEY"

# Expected response:
# {"clinics": [...]}  or  {"clinics": []}


# 3. Admin login
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"YourPassword"}'

# Expected response:
# {"access_token":"eyJ...","token_type":"bearer"}


# 4. Chatbot
curl -X POST http://localhost:8000/chatbot/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","conversation_id":"test-001"}'

# Expected response:
# {"response":"Hello! How can I help you today?","conversation_id":"test-001"}
```

---

## Application URLs

| Interface | URL | Purpose |
|-----------|-----|---------|
| Chatbot (Home) | http://localhost:5173 | Patient-facing appointment booking |
| Admin Portal | http://localhost:5173/admin/login | Manage clinics and doctors |
| Doctor Portal | http://localhost:5173/doctor/login | Doctor dashboard and appointments |
| API Documentation | http://localhost:8000/docs | Interactive Swagger UI |
| Health Check | http://localhost:8000/health | Backend status |

---

## Restarting the Project

Every time you open a new terminal session, follow these steps:

**Terminal 1 — Backend:**
```bash
cd dcbc
source venv/bin/activate    # Linux/macOS
# or: .\venv\Scripts\Activate.ps1  (Windows PowerShell)
python run.py
```

**Terminal 2 — Frontend:**
```bash
cd dcbc/frontend
npm run dev
```

---

## Troubleshooting

### `(venv)` not showing after activation (Windows)

PowerShell may block script execution. Run this once as Administrator:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then retry `.\venv\Scripts\Activate.ps1`

---

### `could not connect to server` — PostgreSQL not running

```bash
# Linux (systemd)
sudo systemctl start postgresql

# macOS (Homebrew)
brew services start postgresql

# Windows — open Services, find "postgresql-x64-14" and click Start
```

---

### `ValidationError` on backend startup — missing environment variable

A required `.env` field is empty or missing. Double-check that all fields from Step 3.5 are filled in with real values (not placeholder text).

---

### `alembic upgrade head` fails — `relation already exists`

The database already has tables. Run:

```bash
alembic stamp head
```

This marks the current state as up-to-date without re-running migrations.

---

### Admin login returns `401 Unauthorized`

The `ADMIN_PASSWORD_HASH` does not match your password. Regenerate it:

```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourPassword'))"
```

Update `ADMIN_PASSWORD_HASH` in `.env` and restart the backend.

---

### Frontend shows blank page or network errors

Ensure the frontend `.env` file exists inside the `frontend/` folder:

```bash
# Should output: VITE_API_URL=http://localhost:8000
cat frontend/.env
```

If missing, recreate it:
```bash
echo "VITE_API_URL=http://localhost:8000" > frontend/.env
```

Then restart the frontend (`Ctrl+C`, then `npm run dev` again).

---

### Chatbot not responding — OpenAI errors

Verify your API key is valid and has available credits:
- Check key at: https://platform.openai.com/api-keys
- Check usage at: https://platform.openai.com/usage
