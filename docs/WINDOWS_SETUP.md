# Windows Setup Guide for Calendar Booking Project

## Step 1: Install PostgreSQL on Windows

### Option A: Using Chocolatey (Recommended - Fastest)
If you have Chocolatey installed:
```powershell
choco install postgresql
```

### Option B: Using Winget (Built-in Windows Package Manager)
```powershell
winget install PostgreSQL.PostgreSQL
```

### Option C: Manual Installation
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer (postgresql-16.x-windows-x64.exe)
3. During installation:
   - Set a password for the 'postgres' user (remember this!)
   - Use default port: 5432
   - Use default locale
4. Add PostgreSQL to PATH:
   - Default location: `C:\Program Files\PostgreSQL\16\bin`

### Verify Installation
After installation, open a NEW PowerShell window and run:
```powershell
psql --version
```

## Step 2: Configure PostgreSQL

### Start PostgreSQL Service (if not running)
```powershell
# Check service status
Get-Service -Name postgresql*

# Start service if stopped
Start-Service -Name postgresql-x64-16  # or your PostgreSQL service name
```

### Create Database
Open PowerShell and run:
```powershell
# Connect to PostgreSQL
psql -U postgres

# In psql prompt, create database:
CREATE DATABASE calendar_booking_db;

# Create a user (optional but recommended)
CREATE USER calendar_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE calendar_booking_db TO calendar_user;

# Exit psql
\q
```

## Step 3: Install Python Dependencies

The virtual environment already exists. Activate it and install dependencies:
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

1. Copy `env.example` to `.env`
2. Edit `.env` with your settings

## Step 5: Run Database Migrations

```powershell
# Make sure virtual environment is activated
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Step 6: Run the Application

```powershell
python run.py
```

Or:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Quick Setup Script

Run this after PostgreSQL is installed:
```powershell
.\setup.ps1
```

## Troubleshooting

### PostgreSQL Not in PATH
Add manually:
```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
```

### Virtual Environment Activation Error
If you get execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Database Connection Error
- Verify PostgreSQL service is running
- Check DATABASE_URL in .env file
- Ensure database exists: `psql -U postgres -l`
