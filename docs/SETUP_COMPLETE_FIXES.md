# End-to-End Setup Summary

## ✅ All Fixes Applied

### 1. Fixed Endpoint Path
**File**: `chatbot-service/app/services/calendar_client.py`
- **Changed**: `/api/v1/doctors/export` → `/api/v1/appointments/doctors/export`
- **Reason**: The export endpoint is under the appointments router, not doctors router

### 2. Fixed Port Configuration
**Files**: 
- `chatbot-service/app/core/config.py`
- `chatbot-service/env.example`

- **Changed**: `http://localhost:8005` → `http://localhost:8000`
- **Reason**: Calendar service now runs on port 8000 (as configured in `run.py`)

### 3. Improved Error Handling
**File**: `chatbot-service/app/services/calendar_client.py`
- Added detailed logging for 401 authentication errors
- Better error messages showing API key (masked) and service URL
- Helps debug connection issues

### 4. Updated Configuration Files
- Updated `chatbot-service/env.example` with correct port
- Updated `start_all_services.sh` to check correct ports

## 🔧 Required Configuration

### Calendar Service `.env` (Root Directory)
```env
SERVICE_API_KEY=dev-api-key
DATABASE_URL=postgresql://user:password@localhost:5432/calendar_booking_db
# ... other required variables
```

### Chatbot Service `.env`
```env
CALENDAR_SERVICE_URL=http://localhost:8000
CALENDAR_SERVICE_API_KEY=dev-api-key
OPENAI_API_KEY=your_openai_api_key_here
# ... other variables
```

**CRITICAL**: Both `SERVICE_API_KEY` (calendar) and `CALENDAR_SERVICE_API_KEY` (chatbot) must be `dev-api-key` for development.

## 🚀 Starting Services

### Option 1: Manual Start (Recommended for Development)

**Terminal 1 - Calendar Service:**
```bash
cd c:\Lakshay\Calender-booking
python run.py
```
Runs on: http://localhost:8000

**Terminal 2 - Chatbot Service:**
```bash
cd c:\Lakshay\Calender-booking\chatbot-service
python run_chatbot.py
```
Runs on: http://localhost:8001

**Terminal 3 - Frontend:**
```bash
cd c:\Lakshay\Calender-booking\chatbot-frontend
npm start
```
Runs on: http://localhost:3000

### Option 2: Docker Compose
```bash
docker-compose up --build
```

## ✅ Verification

### 1. Check Calendar Service
```bash
curl http://localhost:8000/health
```

### 2. Check Chatbot Service
```bash
curl http://localhost:8001/api/v1/health/
```

### 3. Test API Connection
```bash
curl -H "X-API-Key: dev-api-key" http://localhost:8000/api/v1/appointments/doctors/export
```

### 4. Run Verification Script
```bash
python verify_config.py
```

## 🔍 Troubleshooting

### 401 Unauthorized Errors
- ✅ **Fixed**: Endpoint path corrected
- ✅ **Fixed**: Port configuration updated
- ⚠️ **Action Required**: Ensure API keys match in both `.env` files

### Connection Errors
- Verify calendar service is running on port 8000
- Check `CALENDAR_SERVICE_URL` in chatbot `.env` is `http://localhost:8000`
- Verify API key is `dev-api-key` in both services

### Database Errors
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in root `.env`
- Run migrations: `alembic upgrade head`

## 📊 Service Architecture

```
Frontend (3000)
    ↓
Chatbot Service (8001)
    ↓ [X-API-Key: dev-api-key]
Calendar Service (8000)
    ↓
PostgreSQL Database
```

## 📝 Next Steps

1. **Verify Configuration**:
   - Run `python verify_config.py`
   - Check all services are accessible

2. **Test End-to-End**:
   - Open http://localhost:3000
   - Send a test message to the chatbot
   - Verify it can fetch doctor data from calendar service

3. **Monitor Logs**:
   - Check calendar service logs for API requests
   - Check chatbot service logs for connection status
   - Look for any 401 errors (should be resolved now)

## 🎯 Expected Behavior

After applying all fixes:
- ✅ Chatbot can successfully call `/api/v1/appointments/doctors/export`
- ✅ No more 401 Unauthorized errors
- ✅ Doctor data is fetched and used in chatbot responses
- ✅ End-to-end flow works: Frontend → Chatbot → Calendar → Database

---

**All fixes have been applied. The project should now run end-to-end!** 🎉