# 🚀 START HERE - Calendar Booking Project Setup

## ✅ COMPLETED AUTOMATICALLY

I've successfully set up the following for you:

1. ✅ **Virtual Environment** - Created at `.\venv\`
2. ✅ **All Python Dependencies Installed**:
   - FastAPI 0.128.0
   - Uvicorn 0.40.0
   - Pydantic 2.12.5
   - SQLAlchemy 2.0.45
   - Alembic 1.18.1
   - psycopg2-binary 2.9.11
   - Google Calendar API libraries
   - All other requirements
3. ✅ **PostgreSQL 16 Installed** at `C:\Program Files\PostgreSQL\16`
4. ✅ **.env Configuration File** created
5. ✅ **Helper Scripts Created** for easy setup

## ⚠️ REQUIRES YOUR ACTION (3 Simple Steps)

### 📋 Prerequisites Check

Open PowerShell and run:

```powershell
# Add PostgreSQL to PATH for current session
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Verify PostgreSQL is installed
psql --version
# Should show: psql (PostgreSQL) 16.11
```

### Step 1️⃣: Start PostgreSQL Service

PostgreSQL is installed but needs to be started. Choose one method:

**Method A - Using Windows Services (Recommended):**

```powershell
# Find the PostgreSQL service
Get-Service -Name *postgres* | Format-Table -AutoSize

# Start the service (replace with actual service name)
Start-Service -Name "postgresql-x64-16"
```

**Method B - Using pg_ctl:**

```powershell
# Navigate to PostgreSQL directory
cd "C:\Program Files\PostgreSQL\16\bin"

# Start PostgreSQL
.\pg_ctl -D "C:\Program Files\PostgreSQL\16\data" start
```

**Method C - Register as Windows Service (if not registered):**

```powershell
# Run as Administrator
cd "C:\Program Files\PostgreSQL\16\bin"

.\pg_ctl register -N "postgresql-16" -D "C:\Program Files\PostgreSQL\16\data"
Start-Service -Name "postgresql-16"
```

### Step 2️⃣: Create Database

```powershell
# Navigate to project directory
cd C:\Lakshay\Calender-booking

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Create the database using Python script
python create_database.py
```

**The script will prompt for:**
- PostgreSQL password (set during installation, default might be 'postgres')

**Alternative Manual Method:**

```powershell
# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Create database (enter password when prompted)
psql -U postgres -c "CREATE DATABASE calendar_booking_db;"
```

### Step 3️⃣: Update .env and Run Migrations

1. **Edit `.env` file** and update the DATABASE_URL:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/calendar_booking_db
```

Replace `YOUR_PASSWORD` with your actual PostgreSQL password.

2. **Run migrations:**

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run migrations
python run_migrations.py

# OR use alembic directly
alembic upgrade head
```

### Step 4️⃣: Start the Application! 🎉

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Start the server
python run.py
```

**Access your application at:**
- 📄 **Swagger API Docs:** http://localhost:8000/docs
- 📘 **ReDoc:** http://localhost:8000/redoc
- 🔗 **API Endpoint:** http://localhost:8000

## 🎯 Quick Command Reference

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 2. Add PostgreSQL to PATH (if not permanent)
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# 3. Create database (first time only)
python create_database.py

# 4. Run migrations
alembic upgrade head

# 5. Start the server
python run.py
```

## 📁 Helper Scripts Available

| Script | Purpose | Command |
|--------|---------|---------|
| `create_database.py` | Create PostgreSQL database | `python create_database.py` |
| `run_migrations.py` | Run Alembic migrations | `python run_migrations.py` |
| `run.py` | Start FastAPI server | `python run.py` |
| `setup_database.ps1` | PowerShell database setup | `.\setup_database.ps1` |
| `start_app.ps1` | PowerShell app launcher | `.\start_app.ps1` |

## 🔧 Configuration Files

- **`.env`** - Environment variables (DATABASE_URL, API keys, etc.)
- **`alembic.ini`** - Database migration configuration
- **`requirements.txt`** - Python dependencies (already installed)

## 📚 Documentation Files

- **`START_HERE.md`** - This file (quick start guide)
- **`AUTOMATED_SETUP.md`** - Detailed automated setup guide
- **`WINDOWS_SETUP.md`** - Windows-specific setup instructions
- **`SETUP_COMPLETE.md`** - Comprehensive setup documentation
- **`README.md`** - Full project documentation
- **`QUICKSTART.md`** - API usage examples

## 🧪 Test Your Setup

### 1. Test Database Connection

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Test connection
python -c "from app.database import engine; print('✅ Database connection successful!' if engine else '❌ Connection failed')"
```

### 2. Test API (after starting server)

Visit http://localhost:8000/docs and try the interactive API documentation.

### 3. Create a Test Doctor

```bash
curl -X POST "http://localhost:8000/api/v1/doctors/" \
  -H "X-API-Key: dev-secret-key-change-in-production-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_id": "00000000-0000-0000-0000-000000000001",
    "name": "Dr. Jane Smith",
    "email": "dr.smith@example.com",
    "specialization": "Cardiology",
    "experience_years": 15,
    "languages": ["English"],
    "consultation_type": "In-person",
    "general_working_days_text": "Monday to Friday, 9 AM to 5 PM",
    "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "working_hours": {"start": "09:00", "end": "17:00"},
    "slot_duration_minutes": 30
  }'
```

## ❗ Common Issues & Solutions

### Issue: "psql is not recognized"

```powershell
# Add to PATH for current session
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# OR add permanently (Run PowerShell as Administrator)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\16\bin", "Machine")
# Then restart terminal
```

### Issue: "Could not connect to server"

**PostgreSQL is not running. Start it:**

```powershell
Start-Service -Name "postgresql-x64-16"
# OR
cd "C:\Program Files\PostgreSQL\16\bin"
.\pg_ctl -D "C:\Program Files\PostgreSQL\16\data" start
```

### Issue: "Password authentication failed"

**Reset PostgreSQL password:**

1. Edit `C:\Program Files\PostgreSQL\16\data\pg_hba.conf` (as Administrator)
2. Change all `md5` or `scram-sha-256` to `trust`
3. Restart PostgreSQL
4. Connect and change password:
   ```powershell
   psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
   ```
5. Change `trust` back to `scram-sha-256` in pg_hba.conf
6. Restart PostgreSQL again

### Issue: "Module not found" errors

```powershell
# Reinstall dependencies
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: "Database does not exist"

```powershell
# Create it using the script
python create_database.py

# OR manually
psql -U postgres -c "CREATE DATABASE calendar_booking_db;"
```

## 🎓 Learning Resources

### Project Architecture

- **Database** = Single source of truth for all data
- **Google Calendar** = Mirror of confirmed appointments (sync after DB commit)
- **RAG** = Read-only for doctor descriptive data

### Key Endpoints

- `POST /api/v1/doctors/` - Create doctor
- `GET /api/v1/appointments/availability/{doctor_id}` - Check available slots
- `POST /api/v1/appointments/` - Book appointment
- `PUT /api/v1/appointments/{id}/reschedule` - Reschedule
- `DELETE /api/v1/appointments/{id}` - Cancel

## 📞 Next Steps

1. ✅ Start PostgreSQL service
2. ✅ Create database
3. ✅ Run migrations
4. ✅ Start the application
5. 🎉 Test the API at http://localhost:8000/docs
6. 📖 Read API documentation
7. 🔧 Configure Google Calendar (optional)
8. 🤖 Set up RAG service integration (optional)

## 💡 Pro Tips

1. **Always activate virtual environment** before running Python commands
2. **PostgreSQL must be running** before starting the app
3. **Use Swagger UI** at /docs for easy API testing
4. **Check server logs** for detailed error messages
5. **Keep .env secure** - never commit to git

---

## 🆘 Still Having Issues?

If you encounter problems:

1. Check PostgreSQL is running: `Get-Process postgres`
2. Verify `.env` DATABASE_URL is correct
3. Look at application logs in terminal
4. Try restarting PostgreSQL service
5. Review the detailed documentation files

## ✨ Ready to Go!

Once you complete the 4 steps above, your Calendar Booking service will be fully operational!

**Happy Coding! 🚀**
