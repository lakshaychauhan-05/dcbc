# Railway Deployment Guide

This guide explains how to deploy the Calendar Booking Platform on Railway.

## Architecture Overview

The platform consists of 2 services deployed separately:

| Service | Type | Port | Description |
|---------|------|------|-------------|
| Backend API | FastAPI | 8000 | Unified backend (Core API + Doctor Portal + Admin Portal + Chatbot) |
| Frontend | React/Vite | 80 | Unified frontend (Chatbot + Doctor Portal + Admin Portal) |

### API Endpoints Structure

```
Backend (port 8000):
├── /api/v1/*           → Core Calendar API (clinics, doctors, patients, appointments)
├── /portal/*           → Doctor Portal routes (auth, dashboard)
├── /admin/*            → Admin Portal routes (auth, management)
├── /chatbot/api/v1/*   → Chatbot API routes
└── /health             → Health check

Frontend (port 80):
├── /                   → Chatbot (main page)
├── /doctor/*           → Doctor Portal
└── /admin/*            → Admin Portal
```

## Prerequisites

1. Railway account (https://railway.app)
2. GitHub repository with the code
3. PostgreSQL database (provision on Railway)
4. OpenAI API key (for chatbot)
5. Google Cloud service account credentials (optional, for calendar sync)

## Step-by-Step Deployment

### Step 1: Create Railway Project

```bash
# Login to Railway CLI (optional)
railway login

# Create new project
railway init
```

Or create via Railway dashboard at https://railway.app/new

### Step 2: Provision PostgreSQL Database

1. In Railway dashboard, click **+ New**
2. Select **Database** → **PostgreSQL**
3. Railway will automatically provide `DATABASE_URL`
4. Copy this URL for backend configuration

### Step 3: Deploy Backend API

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Set root directory to `/` (project root)
4. Railway will detect the `Dockerfile`

**Required Environment Variables:**

```bash
# Database (from Railway PostgreSQL)
DATABASE_URL=<from PostgreSQL service>

# Server
PORT=8000
DEBUG=false
DEFAULT_TIMEZONE=Asia/Kolkata

# Core API Auth
SERVICE_API_KEY=<generate secure random key>
API_KEY_RATE_LIMIT_PER_MINUTE=120
API_KEY_RATE_LIMIT_BURST=30

# Doctor Portal Auth
DOCTOR_PORTAL_JWT_SECRET=<generate secure random key>
DOCTOR_PORTAL_JWT_ALGORITHM=HS256

# Admin Portal Auth
ADMIN_PORTAL_JWT_SECRET=<generate secure random key>
ADMIN_PORTAL_JWT_ALGORITHM=HS256
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=<bcrypt hash of admin password>

# Chatbot (OpenAI)
OPENAI_API_KEY=<your OpenAI API key>
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=500

# Google Calendar (optional - disabled by default)
DISABLE_CALENDAR_WORKERS=true
GOOGLE_CALENDAR_CREDENTIALS_PATH=
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=

# CORS (update after frontend deployment)
CORS_ALLOW_ORIGINS=https://<frontend-domain>.railway.app
```

**Generate Admin Password Hash:**
```python
import bcrypt
password = "YourSecurePassword123"
hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(hash)
```

### Step 4: Deploy Frontend

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - **Root Directory:** `frontend`
   - Railway will detect `frontend/Dockerfile`

**Required Environment Variables (Build Args):**

```bash
VITE_API_URL=https://<backend-domain>.railway.app
```

**Note:** For Railway, you may need to set this as a build variable. Add it in the service settings under Variables.

### Step 5: Configure OAuth (Optional)

If using Google OAuth for doctor login:

1. Create OAuth credentials in Google Cloud Console
2. Add authorized redirect URI: `https://<backend-domain>.railway.app/portal/auth/oauth/google/callback`
3. Set these backend environment variables:

```bash
DOCTOR_PORTAL_OAUTH_CLIENT_ID=<google oauth client id>
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET=<google oauth secret>
DOCTOR_PORTAL_OAUTH_REDIRECT_URI=https://<backend-domain>.railway.app/portal/auth/oauth/google/callback
DOCTOR_PORTAL_FRONTEND_CALLBACK_URL=https://<frontend-domain>.railway.app/doctor/oauth/callback
```

### Step 6: Update CORS Origins

After both services are deployed, update backend CORS:

```bash
CORS_ALLOW_ORIGINS=https://<frontend-domain>.railway.app
```

## Environment Variables Reference

### Backend Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection string |
| PORT | No | Server port (default: 8000) |
| DEBUG | No | Enable debug mode (default: false) |
| SERVICE_API_KEY | Yes | API key for external access |
| DOCTOR_PORTAL_JWT_SECRET | Yes | JWT secret for doctor auth |
| ADMIN_PORTAL_JWT_SECRET | Yes | JWT secret for admin auth |
| ADMIN_EMAIL | Yes | Admin login email |
| ADMIN_PASSWORD_HASH | Yes | Bcrypt hash of admin password |
| OPENAI_API_KEY | Yes | OpenAI API key for chatbot |
| CORS_ALLOW_ORIGINS | Yes | Frontend domain |
| DISABLE_CALENDAR_WORKERS | No | Disable Google Calendar sync (default: true) |

### Frontend Variables

| Variable | Required | Description |
|----------|----------|-------------|
| VITE_API_URL | Yes | Backend API URL |

## Health Checks

Both services expose health endpoints:
- Backend: `GET /health`
- Frontend: `GET /health`

Railway automatically monitors these endpoints.

## Verification

After deployment, verify all endpoints:

```bash
# Backend health
curl https://<backend-domain>.railway.app/health

# Frontend health
curl https://<frontend-domain>.railway.app/health

# API test
curl https://<backend-domain>.railway.app/api/v1/clinics \
  -H "X-API-Key: <your-service-api-key>"
```

## Google Calendar Setup (Optional)

If you want to enable Google Calendar sync:

1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create a service account with domain-wide delegation
4. Download the JSON credentials
5. Upload credentials to Railway (or use environment variable)
6. Set environment variables:
   ```bash
   DISABLE_CALENDAR_WORKERS=false
   GOOGLE_CALENDAR_CREDENTIALS_PATH=/app/credentials/your-credentials.json
   GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=admin@yourdomain.com
   ```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correctly set
- Ensure PostgreSQL service is running
- Check Railway logs for connection errors

### CORS Errors
- Update CORS_ALLOW_ORIGINS with exact frontend domain
- Don't include trailing slashes
- Use HTTPS URLs only

### Build Failures
- Check Railway build logs
- Verify Dockerfile exists in correct location
- Ensure all required files are in repository

### Frontend Not Loading
- Verify VITE_API_URL points to correct backend
- Check browser console for API errors
- Verify backend CORS includes frontend domain

### OAuth Redirect Issues
- Verify redirect URIs match exactly in Google Console
- Check DOCTOR_PORTAL_OAUTH_REDIRECT_URI
- Ensure frontend callback URL is correct

## Custom Domains (Optional)

For each service in Railway:
1. Go to service **Settings** → **Domains**
2. Add your custom domain
3. Configure DNS CNAME record
4. Railway provides automatic SSL

## Local Development with Docker

```bash
# Start all services
docker-compose up --build

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - PostgreSQL: localhost:5432
```

## Scaling

Railway supports horizontal scaling:
1. Go to service **Settings**
2. Adjust number of replicas
3. Backend scales independently of frontend

## Monitoring

Use Railway's built-in metrics:
- CPU/Memory usage
- Request latency
- Error rates
- Log streaming

## Cost Optimization

- Use Railway's usage-based pricing
- Scale down during low-traffic periods
- Share PostgreSQL instance for all data
- Chatbot uses OpenAI (pay per token)
