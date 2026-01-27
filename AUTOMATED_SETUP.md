# Automated Setup Guide - Calendar Booking Project

## ✅ What's Already Done

1. ✅ **Virtual Environment** - Created at `.\venv`
2. ✅ **Python Dependencies** - All packages installed:
   - FastAPI, Uvicorn, Pydantic
   - SQLAlchemy, Alembic, psycopg2-binary
   - Google Calendar API libraries
   - httpx, python-dotenv
3. ✅ **PostgreSQL 16** - Installed at `C:\Program Files\PostgreSQL\16`
4. ✅ **.env File** - Created from template

## 🚀 Quick Start (3 Steps)

### Step 1: Add PostgreSQL to PATH

Open a **NEW PowerShell window** and run:

```powershell
# Add to PATH for current session
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Verify PostgreSQL is accessible
psql --version
```

**Optional - Add to PATH permanently:**

```powershell
# Run PowerShell as Administrator
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\16\bin", "Machine")
```

Then restart your terminal.

### Step 2: Create Database

```powershell
# Navigate to project directory
cd C:\Lakshay\Calender-booking

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run database creation script
python create_database.py
```

This will prompt for your PostgreSQL password (set during PostgreSQL installation).

**Note:** If you don't remember the password, default is usually `postgres` for development setups.

### Step 3: Update .env and Run Migrations

Edit `.env` file and update the DATABASE_URL with your PostgreSQL password:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/calendar_booking_db
```

Then run migrations:

```powershell
python run_migrations.py
```

### Step 4: Start the Application

```powershell
python run.py
```

Visit:
- **API Docs:** http://localhost:8000/docs
- **API:** http://localhost:8000

## 🎯 One-Command Setup (After PostgreSQL PATH is set)

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Create database (will prompt for password)
python create_database.py

# Update .env with your PostgreSQL password, then:
python run_migrations.py

# Start the server
python run.py
```

## 📁 Helper Scripts Created

| Script | Purpose |
|--------|---------|
| `create_database.py` | Creates PostgreSQL database interactively |
| `run_migrations.py` | Runs Alembic database migrations |
| `run.py` | Starts the FastAPI application |
| `setup_database.ps1` | PowerShell script for database setup |
| `start_app.ps1` | PowerShell script to start the app |

## 🔧 Configuration

### Database Connection

Edit `.env` and update these values:

```env
# Update with your PostgreSQL password
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/calendar_booking_db

# API security (change for production)
SERVICE_API_KEY=dev-secret-key-change-in-production-12345
```

### Google Calendar (Optional)

For Google Calendar integration:

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create Service Account with domain-wide delegation
4. Download JSON credentials
5. Create `credentials` folder and place JSON file there
6. Update `.env`:

```env
GOOGLE_CALENDAR_CREDENTIALS_PATH=./credentials/google-service-account.json
GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL=admin@yourdomain.com
```

## 🧪 Testing the API

Once the server is running, visit http://localhost:8000/docs

### Quick Test - Create a Doctor

```bash
curl -X POST "http://localhost:8000/api/v1/doctors/" \
  -H "X-API-Key: dev-secret-key-change-in-production-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_id": "00000000-0000-0000-0000-000000000001",
    "name": "Dr. John Doe",
    "email": "dr.john@example.com",
    "specialization": "General Medicine",
    "experience_years": 10,
    "languages": ["English"],
    "consultation_type": "In-person",
    "general_working_days_text": "Monday to Friday",
    "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "working_hours": {"start": "09:00", "end": "17:00"},
    "slot_duration_minutes": 30
  }'
```

## ❗ Troubleshooting

### Issue: "psql is not recognized"

**Solution:** Add PostgreSQL to PATH

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
psql --version
```

### Issue: "Could not connect to PostgreSQL"

**Solution:** Check if PostgreSQL service is running

```powershell
# Check PostgreSQL processes
Get-Process -Name postgres -ErrorAction SilentlyContinue

# If not running, initialize PostgreSQL data directory (if needed)
& "C:\Program Files\PostgreSQL\16\bin\initdb" -D "C:\Program Files\PostgreSQL\16\data"

# Start PostgreSQL
& "C:\Program Files\PostgreSQL\16\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\16\data" -l logfile start
```

### Issue: "Password authentication failed"

**Solution:** Reset PostgreSQL password

1. Edit `C:\Program Files\PostgreSQL\16\data\pg_hba.conf`
2. Change all `md5` to `trust`
3. Restart PostgreSQL
4. Run: `psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"`
5. Change back to `md5` in pg_hba.conf
6. Restart PostgreSQL

### Issue: "Database already exists"

**Solution:** This is OK! Just run migrations:

```powershell
python run_migrations.py
```

### Issue: Migration errors

**Solution:** If migrations folder is empty, create initial migration:

```powershell
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 📚 Additional Resources

- **README.md** - Full project documentation
- **QUICKSTART.md** - API usage guide
- **WINDOWS_SETUP.md** - Detailed Windows setup guide
- **SETUP_COMPLETE.md** - Comprehensive setup instructions

## 🎉 Success Checklist

- [ ] PostgreSQL installed and in PATH
- [ ] Virtual environment activated
- [ ] Database created (`calendar_booking_db`)
- [ ] .env file configured with correct DATABASE_URL
- [ ] Migrations run successfully
- [ ] Server starts without errors
- [ ] Can access http://localhost:8000/docs

## 💡 Tips

1. **Always activate the virtual environment** before running Python commands
2. **Keep PostgreSQL password secure** - change from default in production
3. **Check logs** if something fails - they show detailed error messages
4. **Use Swagger UI** at /docs for easy API testing
5. **PostgreSQL must be running** before starting the application

## 🆘 Need Help?

If you encounter issues:

1. Check that PostgreSQL is running: `Get-Process postgres`
2. Verify DATABASE_URL in .env is correct
3. Check server logs for detailed error messages
4. Ensure virtual environment is activated
5. Try restarting PostgreSQL service

## 📞 Next Steps After Setup

1. **Create a doctor** using the API
2. **Add working hours and leaves** for the doctor
3. **Test appointment booking** functionality
4. **Set up Google Calendar integration** (optional)
5. **Configure RAG service** (optional)
6. **Review API documentation** at /docs
