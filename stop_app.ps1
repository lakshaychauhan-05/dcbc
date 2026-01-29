<#
Stop all services started by start_app.ps1 using PID files in .run.
#>

$ErrorActionPreference = "Stop"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $BaseDir ".run"

if (-Not (Test-Path $runDir)) {
    Write-Host ".run directory not found; nothing to stop." -ForegroundColor Yellow
    exit 0
}

$pidFiles = Get-ChildItem -Path $runDir -Filter "*.pid" -ErrorAction SilentlyContinue
if (-Not $pidFiles) {
    Write-Host "No PID files found; nothing to stop." -ForegroundColor Yellow
    exit 0
}

foreach ($pf in $pidFiles) {
    $procId = Get-Content $pf.FullName | Select-Object -First 1
    if ($procId) {
        try {
            Write-Host "Stopping PID $procId from $($pf.Name)" -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction Stop
        } catch {
            Write-Host "  Could not stop PID $procId ($($_.Exception.Message))" -ForegroundColor DarkYellow
        }
    }
    Remove-Item $pf.FullName -ErrorAction SilentlyContinue
}

Write-Host "Done." -ForegroundColor Green
