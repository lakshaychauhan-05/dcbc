# Start the Calendar Booking Application
# This script activates the virtual environment and starts the server

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Starting Calendar Booking Service" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Check if .env exists
if (-Not (Test-Path ".\.env")) {
    Write-Host "✗ Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy env.example to .env and configure it" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found .env file" -ForegroundColor Green

# Check if virtual environment exists
if (-Not (Test-Path ".\venv")) {
    Write-Host "✗ Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found virtual environment" -ForegroundColor Green
Write-Host ""

Write-Host "Starting FastAPI server..." -ForegroundColor Yellow
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor White
Write-Host "Swagger docs at: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start the application
& .\venv\Scripts\python.exe run.py
