<#
Install all dependencies for the Calendar Booking Platform.
- Python virtual environment with all backend requirements
- Unified frontend (Vite + React)

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

# Ensure Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python found: $($python.Source)" -ForegroundColor Green

# Ensure Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "[ERROR] Node.js not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Node.js found: $($node.Source)" -ForegroundColor Green

Write-Host ""

# Create venv if missing
$venvPath = Join-Path $BaseDir "venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$venvPath"
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists" -ForegroundColor Green
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $pip install --upgrade pip | Out-Null

# Root backend requirements
$requirementsPath = Join-Path $BaseDir "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Host "Installing backend Python dependencies..." -ForegroundColor Yellow
    & $pip install -r $requirementsPath
    Write-Host "[OK] Backend dependencies installed" -ForegroundColor Green
}

Write-Host ""

# Unified frontend dependencies
$frontendPath = Join-Path $BaseDir "frontend"
if (Test-Path $frontendPath) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontendPath
    npm install
    Pop-Location
    Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[WARNING] frontend directory not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Copy .env.example to .env and configure it"
Write-Host "  2. Run: .\scripts\start_app.ps1"
Write-Host ""
