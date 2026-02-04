# Configuration Guide for End-to-End Setup

## Overview
This document outlines the required configuration for all services to work together.

## Service Ports
- **Calendar Service**: Port 8000 (configured in `run.py`)
- **Chatbot Service**: Port 8001 (configured in `chatbot-service/app/core/config.py`)
- **Frontend**: Port 3000/3001 (React app)

## Required Configuration Files

### 1. Root `.env` File (Calendar Service)
Location: `c:\Lakshay\Calender-booking\.env`

Required variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/calendar_booking_db
SERVICE_API_KEY=dev-api-key
GOOGLE_CALENDAR_CREDENTIALS_PATH=./appointment-service-484808-b285efa3864f.json
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=admin@yourdomain.com
WEBHOOK_BASE_URL=http://localhost:8000
GOOGLE_CALENDAR_WEBHOOK_SECRET=your-webhook-secret
DEBUG=true
```

**IMPORTANT**: `SERVICE_API_KEY` must be set to `dev-api-key` to match chatbot service.

### 2. Chatbot Service `.env` File
Location: `c:\Lakshay\Calender-booking\chatbot-service\.env`

Required variables:
```env
OPENAI_API_KEY=your_openai_api_key_here
CALENDAR_SERVICE_URL=http://localhost:8000
CALENDAR_SERVICE_API_KEY=dev-api-key
DEBUG=true
HOST=0.0.0.0
PORT=8001
```

**IMPORTANT**: 
- `CALENDAR_SERVICE_URL` must point to port 8000
- `CALENDAR_SERVICE_API_KEY` must match the calendar service's `SERVICE_API_KEY`

## Fixed Issues

### ✅ Fixed Endpoint Path
- **Before**: `/api/v1/doctors/export`
- **After**: `/api/v1/appointments/doctors/export`
- **File**: `chatbot-service/app/services/calendar_client.py`

### ✅ Fixed Port Configuration
- **Before**: `http://localhost:8005`
- **After**: `http://localhost:8000`
- **Files**: 
  - `chatbot-service/app/core/config.py`
  - `chatbot-service/env.example`

### ✅ Improved Error Handling
- Added detailed logging for 401 authentication errors
- Better error messages for debugging connection issues

## Verification Steps

1. **Check Calendar Service**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check Chatbot Service**:
   ```bash
   curl http://localhost:8001/api/v1/health/
   ```

3. **Test API Connection** (requires API key):
   ```bash
   curl -H "X-API-Key: dev-api-key" http://localhost:8000/api/v1/appointments/doctors/export
   ```

4. **Run Verification Script**:
   ```bash
   python verify_config.py
   ```

## Starting Services

### Start Calendar Service:
```bash
cd c:\Lakshay\Calender-booking
python run.py
```

### Start Chatbot Service:
```bash
cd c:\Lakshay\Calender-booking\chatbot-service
python run_chatbot.py
```

### Start Frontend:
```bash
cd c:\Lakshay\Calender-booking\chatbot-frontend
npm start
```

## Troubleshooting

### 401 Unauthorized Errors
- Verify `SERVICE_API_KEY` in calendar service `.env` matches `CALENDAR_SERVICE_API_KEY` in chatbot `.env`
- Both should be set to `dev-api-key` for development
- Check that the `X-API-Key` header is being sent (check logs)

### Connection Errors
- Verify calendar service is running on port 8000
- Check firewall settings
- Verify `CALENDAR_SERVICE_URL` is correct in chatbot `.env`

### Database Connection Errors
- Verify PostgreSQL is running
- Check `DATABASE_URL` in root `.env` file
- Ensure database exists and migrations are applied

## API Key Security Note
⚠️ **For Production**: Change `dev-api-key` to a strong, randomly generated API key in both services.