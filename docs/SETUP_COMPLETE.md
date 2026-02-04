# Setup Instructions - Final Steps

## Current Status

✅ Virtual environment created
✅ All Python dependencies installed
✅ PostgreSQL 16 installed
✅ .env file created
⚠️ Database needs to be created
⚠️ Database migrations need to be run

## Complete the Setup

### Step 1: Add PostgreSQL to Your PATH Permanently

Open PowerShell as Administrator and run:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\16\bin", "Machine")
```

Then **restart your terminal** for changes to take effect.

### Step 2: Initialize and Create Database

Option A - Using the provided script:

```powershell
# This will prompt for postgres password
.\setup_database.ps1
```

Option B - Manual steps:

```powershell
# Add PostgreSQL to PATH for current session
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Create the database (will prompt for password)
psql -U postgres -c "CREATE DATABASE calendar_booking_db;"
```

**Note:** If you forgot the PostgreSQL password set during installation, you may need to:
1. Edit `C:\Program Files\PostgreSQL\16\data\pg_hba.conf`
2. Change authentication method from `md5` to `trust` temporarily
3. Restart PostgreSQL service
4. Set a new password
5. Change back to `md5` authentication

### Step 3: Update .env File

Edit `.env` and update the DATABASE_URL with your PostgreSQL password:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/calendar_booking_db
```

Replace `YOUR_PASSWORD` with the actual PostgreSQL password.

### Step 4: Run Database Migrations

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run migrations
alembic upgrade head
```

### Step 5: Start the Application

Option A - Using the provided script:

```powershell
.\start_app.ps1
```

Option B - Manual start:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start the server
python run.py
```

The API will be available at:
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Step 6: Test the API

Open your browser and go to: http://localhost:8000/docs

You can test the endpoints using the Swagger UI.

## Troubleshooting

### PostgreSQL Service Not Running

```powershell
# Check service
Get-Service -Name postgresql*

# If not running, you may need to start it manually
& "C:\Program Files\PostgreSQL\16\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\16\data" start
```

### Database Connection Errors

1. Verify PostgreSQL is running
2. Check the DATABASE_URL in .env is correct
3. Verify the database exists: `psql -U postgres -l`

### Migration Errors

If you get migration errors, you might need to create an initial migration:

```powershell
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Quick Reference Commands

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run migrations
alembic upgrade head

# Start development server
python run.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Check PostgreSQL version
psql --version

# Connect to database
psql -U postgres -d calendar_booking_db

# List databases
psql -U postgres -l
```

## Google Calendar Integration (Optional)

To enable Google Calendar integration:

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create a Service Account with domain-wide delegation
4. Download the service account JSON file
5. Create `credentials` folder and place the JSON file there
6. Update these in `.env`:
   - `GOOGLE_CALENDAR_CREDENTIALS_PATH`
   - `GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL`

## Need Help?

- Check logs in the terminal where the server is running
- Visit http://localhost:8000/docs for API documentation
- Review README.md for architecture details
- Review QUICKSTART.md for API usage examples
