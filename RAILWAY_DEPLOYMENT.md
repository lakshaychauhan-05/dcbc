# Railway Deployment Guide

This guide explains how to deploy the Calendar Booking Platform on Railway.

## Architecture Overview

The platform consists of 7 services that need to be deployed:

| Service | Type | Default Port | Description |
|---------|------|--------------|-------------|
| Core Calendar API | Backend | 8000 | Main booking and calendar logic |
| Admin Portal API | Backend | 5050 | Admin management backend |
| Doctor Portal API | Backend | 5000 | Doctor scheduling backend |
| Chatbot API | Backend | 8002 | LLM-powered booking assistant |
| Admin Portal UI | Frontend | 5500 | Admin dashboard |
| Doctor Portal UI | Frontend | 5175 | Doctor dashboard |
| Chatbot UI | Frontend | 3000 | Chat widget |

## Prerequisites

1. Railway account (https://railway.app)
2. Railway CLI installed (optional but recommended)
3. GitHub repository with the code
4. PostgreSQL database (can provision on Railway)
5. Redis instance (can provision on Railway)
6. Google Cloud service account credentials

## Step-by-Step Deployment

### Step 1: Create Railway Project

```bash
# Login to Railway CLI
railway login

# Create new project
railway init
```

Or create via Railway dashboard at https://railway.app/new

### Step 2: Provision PostgreSQL Database

1. In Railway dashboard, click **+ New**
2. Select **Database** → **PostgreSQL**
3. Railway will automatically provide `DATABASE_URL`

### Step 3: Provision Redis (Optional)

1. Click **+ New** → **Database** → **Redis**
2. Railway will provide `REDIS_URL`
3. If not using Redis, the chatbot will use in-memory storage

### Step 4: Deploy Core Calendar API

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Set the root directory to `/` (root)
4. Railway will detect the `Dockerfile` at root

**Environment Variables:**
```
DATABASE_URL=<from PostgreSQL service>
SERVICE_API_KEY=<generate secure key>
GOOGLE_CALENDAR_CREDENTIALS_PATH=./credentials/your-credentials.json
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=your-admin@domain.com
WEBHOOK_BASE_URL=https://<your-railway-domain>
GOOGLE_CALENDAR_WEBHOOK_SECRET=<generate secure key>
DEFAULT_TIMEZONE=Asia/Kolkata
CORS_ALLOW_ORIGINS=https://<admin-frontend>,https://<doctor-frontend>,https://<chatbot-frontend>
```

### Step 5: Deploy Admin Portal API

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `admin_portal`
   - Dockerfile Path: `admin_portal/Dockerfile`

**Environment Variables:**
```
DATABASE_URL=<from PostgreSQL service>
ADMIN_PORTAL_JWT_SECRET=<generate secure key>
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=<bcrypt hash of password>
CORE_API_BASE=https://<core-api-domain>
PORTAL_API_BASE=https://<doctor-portal-api-domain>/portal
CORS_ALLOW_ORIGINS=https://<admin-frontend>
```

### Step 6: Deploy Doctor Portal API

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `doctor_portal`
   - Dockerfile Path: `doctor_portal/Dockerfile`

**Environment Variables:**
```
DATABASE_URL=<from PostgreSQL service>
DOCTOR_PORTAL_JWT_SECRET=<generate secure key>
DOCTOR_PORTAL_OAUTH_CLIENT_ID=<google oauth client id>
DOCTOR_PORTAL_OAUTH_CLIENT_SECRET=<google oauth secret>
DOCTOR_PORTAL_OAUTH_REDIRECT_URI=https://<doctor-api-domain>/portal/auth/oauth/google/callback
DOCTOR_PORTAL_FRONTEND_CALLBACK_URL=https://<doctor-frontend>/oauth/callback
CORS_ALLOW_ORIGINS=https://<doctor-frontend>
```

### Step 7: Deploy Chatbot API

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `chatbot-service`
   - Dockerfile Path: `chatbot-service/Dockerfile`

**Environment Variables:**
```
OPENAI_API_KEY=<your openai api key>
OPENAI_MODEL=gpt-4
CALENDAR_SERVICE_URL=https://<core-api-domain>
CALENDAR_SERVICE_API_KEY=<same as SERVICE_API_KEY>
REDIS_URL=<from Redis service, optional>
CORS_ALLOW_ORIGINS=https://<chatbot-frontend>
```

### Step 8: Deploy Admin Portal Frontend

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `admin-portal-frontend`
   - Dockerfile Path: `admin-portal-frontend/Dockerfile`

**Environment Variables:**
```
VITE_API_BASE_URL=https://<admin-api-domain>
VITE_CORE_API_BASE=https://<core-api-domain>
VITE_PORTAL_API_BASE=https://<doctor-api-domain>/portal
```

### Step 9: Deploy Doctor Portal Frontend

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `doctor-portal-frontend`
   - Dockerfile Path: `doctor-portal-frontend/Dockerfile`

**Environment Variables:**
```
VITE_API_BASE_URL=https://<doctor-api-domain>
VITE_GOOGLE_CLIENT_ID=<google oauth client id>
VITE_OAUTH_REDIRECT_URI=https://<doctor-api-domain>/portal/auth/oauth/google/callback
```

### Step 10: Deploy Chatbot Frontend

1. Click **+ New** → **GitHub Repo**
2. Select your repository
3. Configure:
   - Root Directory: `chatbot-frontend`
   - Dockerfile Path: `chatbot-frontend/Dockerfile`

**Environment Variables:**
```
REACT_APP_CHATBOT_API_URL=https://<chatbot-api-domain>
REACT_APP_CALENDAR_API_URL=https://<core-api-domain>
```

## Service Communication

After all services are deployed, update CORS origins to include all frontend domains:

```
Core API CORS:        https://admin-ui.railway.app,https://doctor-ui.railway.app,https://chatbot-ui.railway.app
Admin API CORS:       https://admin-ui.railway.app
Doctor API CORS:      https://doctor-ui.railway.app
Chatbot API CORS:     https://chatbot-ui.railway.app
```

## Google Calendar Setup

1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create a service account with domain-wide delegation
4. Download the JSON credentials
5. Place credentials in `credentials/` folder
6. Grant calendar access scopes in Google Admin Console

## Custom Domains (Optional)

For each service in Railway:
1. Go to service Settings → Domains
2. Add your custom domain
3. Configure DNS CNAME record
4. Railway provides automatic SSL

## Health Checks

All services expose health endpoints:
- Backend services: `/health`
- Frontend services: `/health` (nginx)

Railway will automatically monitor these endpoints.

## Troubleshooting

### Database Connection Issues
- Ensure DATABASE_URL is correctly set
- Check if PostgreSQL service is running
- Verify network connectivity between services

### CORS Errors
- Update CORS_ALLOW_ORIGINS with all frontend domains
- Include both HTTP and HTTPS if needed
- Don't include trailing slashes

### OAuth Redirect Issues
- Ensure redirect URIs match exactly in Google Console
- Update DOCTOR_PORTAL_OAUTH_REDIRECT_URI
- Update DOCTOR_PORTAL_FRONTEND_CALLBACK_URL

### Container Build Failures
- Check Dockerfile syntax
- Verify all required files are copied
- Review Railway build logs

## Scaling

Railway supports horizontal scaling:
1. Go to service Settings
2. Adjust number of replicas
3. Backend services scale independently

## Monitoring

Use Railway's built-in metrics:
- CPU/Memory usage
- Request latency
- Error rates
- Log streaming

## Cost Optimization

- Use Railway's sleep mode for development
- Scale down non-critical services
- Share PostgreSQL instance across services
- Use Redis only if needed (chatbot works with in-memory fallback)
