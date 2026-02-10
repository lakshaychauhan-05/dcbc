<#
Start all services (core API, doctor portal API, admin portal API, doctor UI, admin UI)
All Python services run in the same venv.
Frontends run via npm in their own directories.
PID files are written to .run\*.pid so stop_app.ps1 can terminate them cleanly.
#>

$ErrorActionPreference = "Stop"
# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Starting Calendar Booking - All Services" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ensure .env
if (-Not (Test-Path ".\.env")) {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy env.example to .env and configure it" -ForegroundColor Yellow
    exit 1
}
Write-Host "Found .env file" -ForegroundColor Green

# Ensure venv
if (-Not (Test-Path ".\venv")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it or run install_all.ps1 first" -ForegroundColor Yellow
    exit 1
}
Write-Host "Found virtual environment" -ForegroundColor Green

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
    Write-Host "Starting $Name" -ForegroundColor Yellow
    $ps = Start-Process -FilePath "powershell" -ArgumentList "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$WorkingDir`"; $Command" -PassThru -WindowStyle Minimized
    if ($PidFile) {
        Set-Content -Path $PidFile -Value $ps.Id
    }
    Write-Host "  $Name PID: $($ps.Id)" -ForegroundColor DarkGray
}

# Python commands (use same venv)
$python = Join-Path $BaseDir "venv\Scripts\python.exe"

$services = @(
    @{ Name = "Core API (8000)"; Command = "& `"$python`" run.py"; Dir = $BaseDir; Pid = Join-Path $runDir "core.pid" },
    @{ Name = "Doctor Portal API (5000)"; Command = "& `"$python`" run_doctor_portal.py"; Dir = $BaseDir; Pid = Join-Path $runDir "doctor_api.pid" },
    @{ Name = "Admin Portal API (5050)"; Command = "& `"$python`" run_admin_portal.py"; Dir = $BaseDir; Pid = Join-Path $runDir "admin_api.pid" },
    @{ Name = "Doctor Portal UI (5175)"; Command = "npm run dev -- --host --port 5175"; Dir = Join-Path $BaseDir "doctor-portal-frontend"; Pid = Join-Path $runDir "doctor_ui.pid" },
    @{ Name = "Admin Portal UI (5500)"; Command = "npm run dev -- --host --port 5500"; Dir = Join-Path $BaseDir "admin-portal-frontend"; Pid = Join-Path $runDir "admin_ui.pid" },
    @{ Name = "Chatbot API (8003)"; Command = "`$env:CHATBOT_PORT='8003'; & `"$python`" chatbot-service/run_chatbot.py"; Dir = $BaseDir; Pid = Join-Path $runDir "chatbot_api.pid" },
    @{ Name = "Chatbot UI (3000)"; Command = "npm run start"; Dir = Join-Path $BaseDir "chatbot-frontend"; Pid = Join-Path $runDir "chatbot_ui.pid" }
)

foreach ($svc in $services) {
    Start-ServiceProcess -Name $svc.Name -Command $svc.Command -WorkingDir $svc.Dir -PidFile $svc.Pid
}

Write-Host ""

# Create logs directory if it doesn't exist
$logsDir = Join-Path $BaseDir "logs"
if (-Not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
    Write-Host "Created logs directory" -ForegroundColor Green
}

$logFile = Join-Path $logsDir "app.log"

Write-Host ""
Write-Host "All processes started. PIDs stored in .run/*.pid" -ForegroundColor Green
Write-Host ""
Write-Host "SERVICE URLS:" -ForegroundColor Cyan
Write-Host "  Core API docs:      http://localhost:8000/docs"
Write-Host "  Chatbot API:        http://localhost:8003"
Write-Host "  Chatbot UI:         http://localhost:3000"
Write-Host "  Doctor portal API:  http://localhost:5000/portal/health"
Write-Host "  Admin portal API:   http://localhost:5050/admin/health"
Write-Host "  Doctor UI:          http://localhost:5175"
Write-Host "  Admin UI:           http://localhost:5500"
Write-Host ""
Write-Host "LOGS:" -ForegroundColor Cyan
Write-Host "  Log file: $logFile"
Write-Host ""
Write-Host "Press Ctrl+C to stop viewing logs (services will keep running)" -ForegroundColor Yellow
Write-Host "Use stop_app.ps1 to stop all services." -ForegroundColor Yellow
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
