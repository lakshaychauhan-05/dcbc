<#
Start unified Calendar Booking Platform:
- Backend: Single FastAPI app on port 8000
- Frontend: Unified React app on port 5173

PID files are written to .run\*.pid so stop_app.ps1 can terminate them cleanly.
#>

$ErrorActionPreference = "Stop"
# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Starting Calendar Booking Platform" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ensure .env
if (-Not (Test-Path ".\.env")) {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Found .env file" -ForegroundColor Green

# Ensure venv
if (-Not (Test-Path ".\venv")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it or run install_all.ps1 first" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Found virtual environment" -ForegroundColor Green

# Check if frontend dependencies are installed
$frontendDir = Join-Path $BaseDir "frontend"
if (-Not (Test-Path $frontendDir)) {
    Write-Host "Error: frontend directory not found!" -ForegroundColor Red
    Write-Host "Please ensure the unified frontend is set up" -ForegroundColor Yellow
    exit 1
}

$nodeModulesDir = Join-Path $frontendDir "node_modules"
if (-Not (Test-Path $nodeModulesDir)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    Pop-Location
}
Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green

# Prepare run state directory
$runDir = Join-Path $BaseDir ".run"
if (-Not (Test-Path $runDir)) { New-Item -ItemType Directory -Path $runDir | Out-Null }

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$Command,
        [string]$WorkingDir = $BaseDir,
        [string]$PidFile
    )
    Write-Host "Starting $Name..." -ForegroundColor Yellow
    $ps = Start-Process -FilePath "powershell" -ArgumentList "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$WorkingDir`"; $Command" -PassThru -WindowStyle Minimized
    if ($PidFile) {
        Set-Content -Path $PidFile -Value $ps.Id
    }
    Write-Host "  $Name started (PID: $($ps.Id))" -ForegroundColor DarkGray
}

# Python command (use venv)
$python = Join-Path $BaseDir "venv\Scripts\python.exe"

# Define services
$services = @(
    @{
        Name = "Backend API (Port 8000)"
        Command = "& `"$python`" run.py"
        Dir = $BaseDir
        Pid = Join-Path $runDir "backend.pid"
    },
    @{
        Name = "Frontend (Port 5173)"
        Command = "npm run dev"
        Dir = $frontendDir
        Pid = Join-Path $runDir "frontend.pid"
    }
)

Write-Host ""

foreach ($svc in $services) {
    Start-ServiceProcess -Name $svc.Name -Command $svc.Command -WorkingDir $svc.Dir -PidFile $svc.Pid
}

# Create logs directory if it doesn't exist
$logsDir = Join-Path $BaseDir "logs"
if (-Not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "app.log"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "All services started successfully!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "SERVICE URLS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Main Application:   http://localhost:5173" -ForegroundColor White
Write-Host "  (Chatbot, Doctor Portal, Admin Portal)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Backend API:        http://localhost:8000" -ForegroundColor White
Write-Host "  API Documentation:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health Check:       http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "FRONTEND ROUTES:" -ForegroundColor Cyan
Write-Host "  Chatbot (Home):     http://localhost:5173/"
Write-Host "  Doctor Login:       http://localhost:5173/doctor/login"
Write-Host "  Admin Login:        http://localhost:5173/admin/login"
Write-Host ""
Write-Host "API ENDPOINTS:" -ForegroundColor Cyan
Write-Host "  Core API:           /api/v1/*"
Write-Host "  Doctor Portal API:  /portal/*"
Write-Host "  Admin Portal API:   /admin/*"
Write-Host "  Chatbot API:        /chatbot/api/v1/*"
Write-Host ""
Write-Host "LOGS:" -ForegroundColor Cyan
Write-Host "  Log file: $logFile"
Write-Host ""
Write-Host "Press Ctrl+C to stop viewing logs (services will keep running)" -ForegroundColor Yellow
Write-Host "Use .\scripts\stop_app.ps1 to stop all services." -ForegroundColor Yellow
Write-Host ""
Write-Host "LIVE LOGS:" -ForegroundColor Cyan
Write-Host ""

# Wait a moment for services to start and create log file
Start-Sleep -Seconds 3

# Show logs in this console (color-coded)
while ($true) {
    if (Test-Path $logFile) {
        Get-Content $logFile -Wait -Tail 100 | ForEach-Object {
            if ($_ -match "ERROR") {
                Write-Host $_ -ForegroundColor Red
            }
            elseif ($_ -match "WARNING") {
                Write-Host $_ -ForegroundColor Yellow
            }
            elseif ($_ -match "Calendar|sync|event|SYNCED|PENDING") {
                Write-Host $_ -ForegroundColor Cyan
            }
            else {
                Write-Host $_
            }
        }
    }
    else {
        Write-Host "Waiting for log file..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
}
