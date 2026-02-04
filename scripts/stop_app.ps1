<#
Stop all services started by start_app.ps1 or start_project.ps1.
Reads PIDs from .run/*.pid (start_app.ps1) or .project-processes.json (start_project.ps1).
#>

$ErrorActionPreference = "Stop"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $BaseDir ".run"
$stateFile = Join-Path $BaseDir ".project-processes.json"

$stopped = 0

# 1) Stop processes from start_project.ps1 (.project-processes.json)
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
                        Write-Host "Stopped $($proc.Name) (PID $pidVal)" -ForegroundColor Yellow
                        $stopped++
                    } catch {
                        Write-Host "Process $($proc.Name) (PID $pidVal) not running." -ForegroundColor DarkGray
                    }
                }
            }
        }
        Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
        # Remove .run/*.pid too so we don't try to stop same PIDs again below
        if (Test-Path $runDir) {
            Get-ChildItem -Path $runDir -Filter "*.pid" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Host "Could not read or stop from .project-processes.json: $($_.Exception.Message)" -ForegroundColor DarkYellow
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
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "Stopped $($pf.BaseName) (PID $procId)" -ForegroundColor Yellow
                $stopped++
            } catch {
                Write-Host "Process PID $procId from $($pf.Name) not running." -ForegroundColor DarkGray
            }
        }
        Remove-Item $pf.FullName -ErrorAction SilentlyContinue
    }
}

if ($stopped -eq 0) {
    if (-Not (Test-Path $stateFile) -and (-Not (Test-Path $runDir) -or -Not (Get-ChildItem -Path $runDir -Filter "*.pid" -ErrorAction SilentlyContinue))) {
        Write-Host "No PID files found; nothing to stop. Run start_app.ps1 or start_project.ps1 first." -ForegroundColor Yellow
    }
} else {
    Write-Host "Done. Stopped $stopped process(es)." -ForegroundColor Green
}
