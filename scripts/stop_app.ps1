<#
Stop all services started by start_app.ps1.
Reads PIDs from .run/*.pid.
#>

$ErrorActionPreference = "Stop"
# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$runDir = Join-Path $BaseDir ".run"
$stateFile = Join-Path $BaseDir ".project-processes.json"

$stopped = 0

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Stopping Calendar Booking Platform" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1) Stop processes from start_project.ps1 (.project-processes.json) - legacy support
if (Test-Path $stateFile) {
    try {
        $processes = Get-Content -Path $stateFile -Raw -ErrorAction Stop | ConvertFrom-Json
        if ($processes) {
            foreach ($proc in $processes) {
                $pidVal = $proc.Id
                if ($pidVal) {
                    try {
                        $p = Get-Process -Id $pidVal -ErrorAction Stop
                        Stop-Process -Id $pidVal -Force -ErrorAction Stop
                        Write-Host "[STOPPED] $($proc.Name) (PID $pidVal)" -ForegroundColor Yellow
                        $stopped++
                    } catch {
                        Write-Host "[SKIP] $($proc.Name) (PID $pidVal) - not running" -ForegroundColor DarkGray
                    }
                }
            }
        }
        Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Could not read .project-processes.json: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}

# 2) Stop processes from start_app.ps1 (.run/*.pid)
if (Test-Path $runDir) {
    $pidFiles = Get-ChildItem -Path $runDir -Filter "*.pid" -ErrorAction SilentlyContinue
    foreach ($pf in $pidFiles) {
        $procId = Get-Content $pf.FullName -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($procId) {
            try {
                $p = Get-Process -Id $procId -ErrorAction Stop

                # Also kill child processes (important for npm/node)
                $childProcesses = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $procId }
                foreach ($child in $childProcesses) {
                    try {
                        Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
                    } catch {}
                }

                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "[STOPPED] $($pf.BaseName) (PID $procId)" -ForegroundColor Yellow
                $stopped++
            } catch {
                Write-Host "[SKIP] $($pf.BaseName) (PID $procId) - not running" -ForegroundColor DarkGray
            }
        }
        Remove-Item $pf.FullName -ErrorAction SilentlyContinue
    }
}

# 3) Also try to stop any orphaned processes on known ports
$portsToCheck = @(8000, 5173)
foreach ($port in $portsToCheck) {
    try {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            try {
                $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($proc) {
                    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                    Write-Host "[STOPPED] Process on port $port (PID $($conn.OwningProcess))" -ForegroundColor Yellow
                    $stopped++
                }
            } catch {}
        }
    } catch {}
}

Write-Host ""
if ($stopped -eq 0) {
    Write-Host "No running services found." -ForegroundColor DarkGray
} else {
    Write-Host "Done. Stopped $stopped process(es)." -ForegroundColor Green
}
Write-Host ""
