<#
Install all dependencies for the project (single Python venv + frontends).
Run this once before start_app.ps1.
#>

$ErrorActionPreference = "Stop"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Installing all project requirements" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Ensure Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    exit 1
}

# Create venv if missing
$venvPath = Join-Path $BaseDir "venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv "$venvPath"
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $pip install --upgrade pip

# Root backend requirements
if (Test-Path (Join-Path $BaseDir "requirements.txt")) {
    Write-Host "Installing backend requirements..." -ForegroundColor Yellow
    & $pip install -r (Join-Path $BaseDir "requirements.txt")
}

# Chatbot service requirements (optional but included for completeness)
if (Test-Path (Join-Path $BaseDir "chatbot-service\requirements.txt")) {
    Write-Host "Installing chatbot-service requirements..." -ForegroundColor Yellow
    & $pip install -r (Join-Path $BaseDir "chatbot-service\requirements.txt")
}

# Frontend dependencies
function Install-NpmDeps {
    param(
        [string]$Path
    )
    if (-Not (Test-Path $Path)) { return }
    Write-Host "Installing npm deps in $Path..." -ForegroundColor Yellow
    Push-Location $Path
    npm install
    Pop-Location
}

Install-NpmDeps -Path (Join-Path $BaseDir "doctor-portal-frontend")
Install-NpmDeps -Path (Join-Path $BaseDir "admin-portal-frontend")
Install-NpmDeps -Path (Join-Path $BaseDir "chatbot-frontend")

Write-Host "✅ All dependencies installed." -ForegroundColor Green
