Param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$stateFile = Join-Path $root ".project-processes.json"

if (-not (Test-Path $stateFile)) {
    Write-Host "No state file found at $stateFile. Nothing to close."
    exit 0
}

$processes = Get-Content -Path $stateFile -Raw | ConvertFrom-Json

foreach ($proc in $processes) {
    try {
        $p = Get-Process -Id $proc.Id -ErrorAction Stop
        Stop-Process -Id $p.Id -Force
        Write-Host "Stopped $($proc.Name) (PID $($proc.Id))"
    } catch {
        Write-Host "Process $($proc.Name) (PID $($proc.Id)) is not running."
    }
}

Remove-Item $stateFile -Force
Write-Host "Closed project processes."
