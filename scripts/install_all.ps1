<#
Install all dependencies for the Calendar Booking Platform.
- Checks Python 3.11+ and Node.js 18+
- Python virtual environment with all backend requirements
- Unified frontend (Vite + React)
- Auto-copies .env.example to .env if missing
- Runs database migrations

Run this once before start_app.ps1.
#>

$ErrorActionPreference = "Stop"
# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Installing Calendar Booking Platform" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Python 3.11+ ──────────────────────────────────────────────
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found in PATH. Install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}
$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor = [int]($pyVersion.Split('.')[0])
$pyMinor = [int]($pyVersion.Split('.')[1])
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
    Write-Host "[ERROR] Python 3.11+ required. Found: $pyVersion" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python $pyVersion found" -ForegroundColor Green

# ── Check Node.js 18+ ────────────────────────────────────────────────
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "[ERROR] Node.js not found in PATH. Install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "[OK] Node.js $nodeVersion found" -ForegroundColor Green

Write-Host ""

# ── Virtual environment ──────────────────────────────────────────────
$venvPath = Join-Path $BaseDir "venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$venvPath"
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists" -ForegroundColor Green
}

$pip        = Join-Path $venvPath "Scripts\pip.exe"
$pythonVenv = Join-Path $venvPath "Scripts\python.exe"

Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $pip install --upgrade pip | Out-Null

# ── Backend Python dependencies ──────────────────────────────────────
$requirementsPath = Join-Path $BaseDir "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Host "Installing backend Python dependencies..." -ForegroundColor Yellow
    & $pip install -r $requirementsPath
    Write-Host "[OK] Backend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] requirements.txt not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ── Frontend dependencies ────────────────────────────────────────────
$frontendPath = Join-Path $BaseDir "frontend"
if (Test-Path $frontendPath) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontendPath
    npm install
    Pop-Location
    Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] frontend directory not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ── Check / create .env file ─────────────────────────────────────────
$envFile    = Join-Path $BaseDir ".env"
$envExample = Join-Path $BaseDir ".env.example"
if (-Not (Test-Path $envFile)) {
    Write-Host "[WARNING] .env file not found." -ForegroundColor Yellow
    if (Test-Path $envExample) {
        Write-Host "  Copying .env.example to .env..." -ForegroundColor Yellow
        Copy-Item $envExample $envFile
        Write-Host "[OK] .env created from .env.example" -ForegroundColor Green
        Write-Host "  >> IMPORTANT: Edit .env and fill in your values before running the app <<" -ForegroundColor Red
    } else {
        Write-Host "[ERROR] .env.example not found. Cannot create .env." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] .env file exists" -ForegroundColor Green
}

Write-Host ""

# ── Database migrations ──────────────────────────────────────────────
Write-Host "Running database migrations..." -ForegroundColor Yellow
$alembicExe = Join-Path $venvPath "Scripts\alembic.exe"

try {
    if (Test-Path $alembicExe) {
        & $alembicExe upgrade head
    } else {
        & $pythonVenv -m alembic upgrade head
    }
    Write-Host "[OK] Database migrations completed" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Migration failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  Ensure DATABASE_URL in .env is correct and PostgreSQL is running." -ForegroundColor Yellow
    Write-Host "  Run manually: alembic upgrade head" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env with your configuration (if not done already)"
Write-Host "  2. Run: .\scripts\start_app.ps1"
Write-Host ""
