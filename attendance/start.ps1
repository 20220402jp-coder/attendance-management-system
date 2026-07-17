$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvDir = if ($env:ATTENDANCE_VENV_DIR) {
    $env:ATTENDANCE_VENV_DIR
} else {
    Join-Path $env:LOCALAPPDATA "AttendanceSystem\venv"
}

$python = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "First run: creating the external Python environment..."
    py -3 -m venv $venvDir
    & $python -m pip install -r requirements.txt
}

$env:PYTHONDONTWRITEBYTECODE = "1"
& $python app.py
