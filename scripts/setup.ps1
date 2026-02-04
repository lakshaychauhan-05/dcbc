# Calendar Booking Project - Windows Setup Script
# Run this script after PostgreSQL is installed

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Calendar Booking Project Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-Not (Test-Path ".\venv")) {
    Write-Host "[1/6] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "[1/6] Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "[2/6] Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "[3/6] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create .env file if it doesn't exist
if (-Not (Test-Path ".\.env")) {
    Write-Host "[5/6] Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".\env.example" ".\.env"
    Write-Host "    ⚠️  IMPORTANT: Edit .env file with your configuration!" -ForegroundColor Red
    Write-Host "    Required changes:" -ForegroundColor Yellow
    Write-Host "      - DATABASE_URL: Update with your PostgreSQL credentials" -ForegroundColor Yellow
    Write-Host "      - SERVICE_API_KEY: Set a secure random key" -ForegroundColor Yellow
    Write-Host "      - Google Calendar credentials (if using)" -ForegroundColor Yellow
} else {
    Write-Host "[5/6] .env file already exists" -ForegroundColor Green
}

# Check if PostgreSQL is accessible
Write-Host "[6/6] Checking PostgreSQL installation..." -ForegroundColor Yellow
try {
    $psqlVersion = psql --version
    Write-Host "    ✓ PostgreSQL found: $psqlVersion" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "1. Edit .env file with your configuration" -ForegroundColor White
    Write-Host "2. Create database:" -ForegroundColor White
    Write-Host "   psql -U postgres -c 'CREATE DATABASE calendar_booking_db;'" -ForegroundColor Gray
    Write-Host "3. Run migrations:" -ForegroundColor White
    Write-Host "   alembic upgrade head" -ForegroundColor Gray
    Write-Host "4. Start the application:" -ForegroundColor White
    Write-Host "   python run.py" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "    ✗ PostgreSQL not found in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "PostgreSQL Installation Required" -ForegroundColor Red
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "Please install PostgreSQL first:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1 - Using winget:" -ForegroundColor White
    Write-Host "  winget install PostgreSQL.PostgreSQL" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2 - Using Chocolatey:" -ForegroundColor White
    Write-Host "  choco install postgresql" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 3 - Manual download:" -ForegroundColor White
    Write-Host "  https://www.postgresql.org/download/windows/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "After installation, open a NEW PowerShell window and run this script again." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup script completed!" -ForegroundColor Green
