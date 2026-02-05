# PostgreSQL Database Setup Script
# This script helps set up the database for the Calendar Booking project

# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "PostgreSQL Database Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

Write-Host "Step 1: Testing PostgreSQL connection..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Please enter the PostgreSQL 'postgres' user password" -ForegroundColor White
Write-Host "(This was set during PostgreSQL installation)" -ForegroundColor Gray
Write-Host ""

# Test connection
$testConnection = Read-Host "Press Enter to continue (or Ctrl+C to cancel)"

Write-Host ""
Write-Host "Creating database 'calendar_booking_db'..." -ForegroundColor Yellow

# Create database using psql
& psql -U postgres -c "CREATE DATABASE calendar_booking_db;"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database created successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create database" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  1. PostgreSQL service is not running" -ForegroundColor White
    Write-Host "  2. Wrong password for 'postgres' user" -ForegroundColor White
    Write-Host "  3. Database already exists (this is OK)" -ForegroundColor White
    Write-Host ""
    Write-Host "To start PostgreSQL service:" -ForegroundColor Yellow
    Write-Host '  & "C:\Program Files\PostgreSQL\16\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\16\data" start' -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Step 2: Verifying database exists..." -ForegroundColor Yellow
& psql -U postgres -l | Select-String "calendar_booking_db"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Database setup complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Update .env file with PostgreSQL password" -ForegroundColor Yellow
Write-Host "2. Run: .\venv\Scripts\python.exe -m alembic upgrade head" -ForegroundColor Yellow
Write-Host "3. Run: .\venv\Scripts\python.exe run.py" -ForegroundColor Yellow
Write-Host ""
