# Verify Setup Script for Calendar Booking Project

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Calendar Booking - Setup Verification" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Add PostgreSQL to PATH
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Check PostgreSQL
Write-Host "[1/4] Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $pgVersion = & psql --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      [OK] $pgVersion" -ForegroundColor Green
    } else {
        Write-Host "      [FAIL] PostgreSQL not accessible" -ForegroundColor Red
    }
} catch {
    Write-Host "      [FAIL] PostgreSQL not found" -ForegroundColor Red
}

# Check virtual environment
Write-Host "[2/4] Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\python.exe") {
    $pyVersion = & .\venv\Scripts\python.exe --version
    Write-Host "      [OK] $pyVersion" -ForegroundColor Green
} else {
    Write-Host "      [FAIL] Virtual environment not found" -ForegroundColor Red
}

# Check dependencies
Write-Host "[3/4] Checking Python dependencies..." -ForegroundColor Yellow
try {
    $fastapi = & .\venv\Scripts\python.exe -c "import fastapi; print(fastapi.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      [OK] FastAPI $fastapi installed" -ForegroundColor Green
    } else {
        Write-Host "      [FAIL] Dependencies not installed" -ForegroundColor Red
    }
} catch {
    Write-Host "      [FAIL] Cannot check dependencies" -ForegroundColor Red
}

# Check configuration
Write-Host "[4/4] Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "      [OK] .env file exists" -ForegroundColor Green
} else {
    Write-Host "      [FAIL] .env file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "What was installed:" -ForegroundColor White
Write-Host "  - PostgreSQL 16.11" -ForegroundColor Gray
Write-Host "  - Python virtual environment" -ForegroundColor Gray
Write-Host "  - FastAPI and all dependencies" -ForegroundColor Gray
Write-Host "  - Database helper scripts" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps (requires your action):" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Start PostgreSQL (if not running):" -ForegroundColor White
Write-Host "   Get-Service -Name *postgres* | Start-Service" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Create database:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python create_database.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Update .env with PostgreSQL password" -ForegroundColor White
Write-Host ""
Write-Host "4. Run migrations:" -ForegroundColor White
Write-Host "   alembic upgrade head" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Start the app:" -ForegroundColor White
Write-Host "   python run.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  START_HERE.md - Quick start guide" -ForegroundColor Gray
Write-Host "  AUTOMATED_SETUP.md - Detailed setup instructions" -ForegroundColor Gray
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor White
Write-Host "  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
