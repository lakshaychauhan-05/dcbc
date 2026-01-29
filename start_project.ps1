Param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$stateFile = Join-Path $root ".project-processes.json"

if (Test-Path $stateFile) {
    Remove-Item $stateFile -Force
}

$processes = @()

function Start-Terminal {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $escapedTitle = $Title.Replace("'", "''")
    $escapedDir = $WorkingDirectory.Replace("'", "''")
    $escapedCommand = $Command.Replace("'", "''")

    $psCommand = "& {`$Host.UI.RawUI.WindowTitle = '$escapedTitle'; Set-Location -LiteralPath '$escapedDir'; $escapedCommand}"
    $proc = Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $psCommand) -PassThru
    return $proc
}

$frontendDir = Join-Path $root "chatbot-frontend"
$frontend = Start-Terminal -Title "Calendar Frontend" -WorkingDirectory $frontendDir -Command "npm start"
$processes += [pscustomobject]@{ Name = "frontend"; Id = $frontend.Id; Command = "npm start"; WorkingDirectory = $frontendDir }

Start-Sleep -Seconds 1

$apiCmd = if (Test-Path "$root\venv\Scripts\python.exe") { ".\venv\Scripts\python.exe run.py" } else { "python run.py" }
$api = Start-Terminal -Title "Calendar API" -WorkingDirectory $root -Command $apiCmd
$processes += [pscustomobject]@{ Name = "calendar-api"; Id = $api.Id; Command = $apiCmd; WorkingDirectory = $root }

Start-Sleep -Seconds 1

$chatbotDir = Join-Path $root "chatbot-service"
$chatbotCmd = if (Test-Path "$root\venv\Scripts\python.exe") { "..\venv\Scripts\python.exe run_chatbot.py" } else { "python run_chatbot.py" }
$chatbot = Start-Terminal -Title "Calendar Chatbot" -WorkingDirectory $chatbotDir -Command $chatbotCmd
$processes += [pscustomobject]@{ Name = "chatbot"; Id = $chatbot.Id; Command = $chatbotCmd; WorkingDirectory = $chatbotDir }

Start-Sleep -Seconds 1

# Admin portal backend (FastAPI, port 5050)
$adminBackendCmd = if (Test-Path "$root\venv\Scripts\python.exe") { ".\venv\Scripts\python.exe run_admin_portal.py" } else { "python run_admin_portal.py" }
$adminBackend = Start-Terminal -Title "Admin Portal API" -WorkingDirectory $root -Command $adminBackendCmd
$processes += [pscustomobject]@{ Name = "admin-portal-api"; Id = $adminBackend.Id; Command = $adminBackendCmd; WorkingDirectory = $root }

Start-Sleep -Seconds 1

# Doctor portal backend (FastAPI, port 5000)
$doctorBackendCmd = if (Test-Path "$root\venv\Scripts\python.exe") { ".\venv\Scripts\python.exe run_doctor_portal.py" } else { "python run_doctor_portal.py" }
$doctorBackend = Start-Terminal -Title "Doctor Portal API" -WorkingDirectory $root -Command $doctorBackendCmd
$processes += [pscustomobject]@{ Name = "doctor-portal-api"; Id = $doctorBackend.Id; Command = $doctorBackendCmd; WorkingDirectory = $root }

Start-Sleep -Seconds 1

# Admin portal frontend (Vite, port 5500)
$adminFrontendDir = Join-Path $root "admin-portal-frontend"
$adminFrontendCmd = "npm run dev -- --host --port 5500"
$adminFrontend = Start-Terminal -Title "Admin Portal UI" -WorkingDirectory $adminFrontendDir -Command $adminFrontendCmd
$processes += [pscustomobject]@{ Name = "admin-portal-ui"; Id = $adminFrontend.Id; Command = $adminFrontendCmd; WorkingDirectory = $adminFrontendDir }

Start-Sleep -Seconds 1

# Doctor portal frontend (Vite, port 5173)
$doctorFrontendDir = Join-Path $root "doctor-portal-frontend"
$doctorFrontendCmd = "npm run dev -- --host --port 5173"
$doctorFrontend = Start-Terminal -Title "Doctor Portal UI" -WorkingDirectory $doctorFrontendDir -Command $doctorFrontendCmd
$processes += [pscustomobject]@{ Name = "doctor-portal-ui"; Id = $doctorFrontend.Id; Command = $doctorFrontendCmd; WorkingDirectory = $doctorFrontendDir }

$processes | ConvertTo-Json -Depth 2 | Set-Content -Path $stateFile -Encoding UTF8

Write-Host "Started project processes. PIDs saved to $stateFile"
