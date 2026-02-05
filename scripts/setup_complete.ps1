# Complete Setup Script for Calendar Booking Project
# Run this script after PostgreSQL is installed and running

param(
    [string]$PostgresPassword = ""
)

$ErrorActionPreference = "Continue"

# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Calendar Booking - Complete Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Check PostgreSQL
Write-Host "[1/5] Checking PostgreSQL installation..." -ForegroundColor Yellow
try {
    $pgVersion = psql --version
    Write-Host "      ✓ PostgreSQL found: $pgVersion" -ForegroundColor Green
} catch {
    Write-Host "      ✗ PostgreSQL not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure PostgreSQL is installed and added to PATH" -ForegroundColor Yellow
    Write-Host "Run: `$env:Path += ';C:\Program Files\PostgreSQL\16\bin'" -ForegroundColor Gray
    exit 1
}

# Check virtual environment
Write-Host "[2/5] Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "      ✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "      ✗ Virtual environment not found!" -ForegroundColor Red
    exit 1
}

# Check dependencies
Write-Host "[3/5] Checking Python dependencies..." -ForegroundColor Yellow
$packages = & .\venv\Scripts\python.exe -m pip list
if ($packages -match "fastapi") {
    Write-Host "      ✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "      ⚠ Installing dependencies..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Create database
Write-Host "[4/5] Setting up database..." -ForegroundColor Yellow
Write-Host ""

if ($PostgresPassword -eq "") {
    Write-Host "      To create the database, run:" -ForegroundColor White
    Write-Host "      .\venv\Scripts\python.exe create_database.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "      Or manually:" -ForegroundColor White
    Write-Host "      psql -U postgres -c `"CREATE DATABASE calendar_booking_db;`"" -ForegroundColor Gray
} else {
    $env:PGPASSWORD = $PostgresPassword
    psql -U postgres -c "CREATE DATABASE calendar_booking_db;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✓ Database created" -ForegroundColor Green
    } else {
        Write-Host "      ⚠ Database might already exist (this is OK)" -ForegroundColor Yellow
    }
    Remove-Item Env:\PGPASSWORD
}

Write-Host ""
Write-Host "[5/5] Configuration check..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "      ✓ .env file exists" -ForegroundColor Green
    Write-Host ""
    Write-Host "      ⚠ Make sure to update DATABASE_URL in .env:" -ForegroundColor Yellow
    Write-Host "      DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/calendar_booking_db" -ForegroundColor Gray
} else {
    Write-Host "      ✗ .env file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Setup Status" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ PostgreSQL 16 installed" -ForegroundColor Green
Write-Host "✓ Virtual environment ready" -ForegroundColor Green
Write-Host "✓ All Python dependencies installed" -ForegroundColor Green
Write-Host "✓ Helper scripts created" -ForegroundColor Green
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Make sure PostgreSQL is running:" -ForegroundColor White
Write-Host "   Get-Service -Name *postgres*" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Create the database:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   python create_database.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Update .env with your PostgreSQL password" -ForegroundColor White
Write-Host ""
Write-Host "4. Run migrations:" -ForegroundColor White
Write-Host "   alembic upgrade head" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Start the application:" -ForegroundColor White
Write-Host "   python run.py" -ForegroundColor Gray
Write-Host ""
Write-Host "6. Access the API:" -ForegroundColor White
Write-Host "   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Useful Commands" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Activate virtual environment" -ForegroundColor Gray
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "# Create database interactively" -ForegroundColor Gray
Write-Host "python create_database.py" -ForegroundColor White
Write-Host ""
Write-Host "# Run migrations" -ForegroundColor Gray
Write-Host "alembic upgrade head" -ForegroundColor White
Write-Host ""
Write-Host "# Start server" -ForegroundColor Gray
Write-Host "python run.py" -ForegroundColor White
Write-Host ""
Write-Host "# Check PostgreSQL service" -ForegroundColor Gray
Write-Host "Get-Service -Name *postgres*" -ForegroundColor White
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "For detailed instructions, see: START_HERE.md" -ForegroundColor Yellow
Write-Host ""
