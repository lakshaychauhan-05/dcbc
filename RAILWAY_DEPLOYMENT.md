# Railway Deployment Guide

Deploy the Calendar Booking Platform on Railway with separate frontend and backend services.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAILWAY PROJECT                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   PostgreSQL    │    │     Backend     │                 │
│  │    (Database)   │───▶│   (FastAPI)     │                 │
│  │                 │    │   Port: 8000    │                 │
│  └─────────────────┘    └────────┬────────┘                 │
│                                  │                           │
│                                  │ API calls                 │
│                                  ▼                           │
│                         ┌─────────────────┐                 │
│                         │    Frontend     │                 │
│                         │  (React/Vite)   │                 │
│                         │    Port: 80     │                 │
│                         └─────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (5 Steps)

### Step 1: Create Railway Project
1. Go to [Railway](https://railway.app) and create a new project
2. Connect your GitHub repository

### Step 2: Add PostgreSQL Database
1. Click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically creates `DATABASE_URL`

### Step 3: Deploy Backend
1. Click **+ New** → **GitHub Repo** → Select your repo
2. Set **Root Directory:** `/` (leave empty)
3. Add environment variables (see table below)

### Step 4: Deploy Frontend
1. Click **+ New** → **GitHub Repo** → Select same repo
2. Set **Root Directory:** `frontend`
3. Add variable: `VITE_API_URL` = `https://<your-backend>.railway.app`

### Step 5: Update Backend CORS
Set backend's `CORS_ALLOW_ORIGINS` to your frontend URL.

---

## Environment Variables

### Backend (Required)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Auto-set by Railway PostgreSQL |
| `SERVICE_API_KEY` | Generate: `openssl rand -hex 32` |
| `DOCTOR_PORTAL_JWT_SECRET` | Generate: `openssl rand -hex 32` |
| `ADMIN_PORTAL_JWT_SECRET` | Generate: `openssl rand -hex 32` |
| `ADMIN_EMAIL` | Admin login email |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash (see below) |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `CORS_ALLOW_ORIGINS` | Your frontend URL |

### Backend (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `DEFAULT_TIMEZONE` | `Asia/Kolkata` | Timezone |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `DISABLE_CALENDAR_WORKERS` | `true` | Disable Google Calendar |

### Frontend (Required)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Your backend URL (e.g., `https://xxx.railway.app`) |

---

## Generate Admin Password Hash

```python
import bcrypt
password = "YourSecurePassword123"
print(bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())
```

Or run: `python scripts/generate_admin_password.py`

---

## Verification

```bash
# Backend health
curl https://<backend>.railway.app/health

# Frontend health
curl https://<frontend>.railway.app/health

# Test API
curl https://<backend>.railway.app/api/v1/clinics \
  -H "X-API-Key: your-api-key"
```

---

## Access Points

| Page | URL |
|------|-----|
| Chatbot (Home) | `https://<frontend>.railway.app/` |
| Doctor Login | `https://<frontend>.railway.app/doctor/login` |
| Admin Login | `https://<frontend>.railway.app/admin/login` |
| API Docs | `https://<backend>.railway.app/docs` |

---

## Troubleshooting

### Frontend shows blank page
- Verify `VITE_API_URL` was set **before** build
- Redeploy frontend after changing variables

### CORS errors in browser
- Check `CORS_ALLOW_ORIGINS` matches exact frontend URL
- No trailing slash, use HTTPS

### API connection fails
- Verify backend is running (check `/health`)
- Check `VITE_API_URL` is correct

### Build fails
- Check Railway build logs
- Verify Dockerfile path is correct

---

## Optional: Google OAuth

For doctor Google login:

```bash
DOCTOR_PORTAL_OAUTH_CLIENT_ID=your-client-id
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET=your-secret
DOCTOR_PORTAL_OAUTH_REDIRECT_URI=https://<backend>.railway.app/portal/auth/oauth/google/callback
DOCTOR_PORTAL_FRONTEND_CALLBACK_URL=https://<frontend>.railway.app/doctor/oauth/callback
```

---

## Local Docker Development

```bash
docker-compose up --build

# Access:
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```
