# Grid-X Worker Setup Script (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "=== Grid-X Worker Setup ===" -ForegroundColor Green
Write-Host ""

# Check Prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

try {
    $PythonVersion = python --version 2>&1
    Write-Host "Python found: $PythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

try {
    $PipVersion = pip --version 2>&1
    Write-Host "pip found" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: pip not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow

$VenvPath = "venv"
if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
    Write-Host "Virtual environment created" -ForegroundColor Green
}
else {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
}

& "$VenvPath\Scripts\Activate.ps1"
Write-Host "Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Install Dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow

python -m pip install --quiet --upgrade pip setuptools wheel

if (Test-Path "worker\requirements.txt") {
    pip install --quiet -r worker\requirements.txt
    Write-Host "Worker dependencies installed" -ForegroundColor Green
}

if (Test-Path "requirements.txt") {
    pip install --quiet -r requirements.txt
    Write-Host "Common dependencies installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the worker, use one of these commands:"
Write-Host "  python -m worker.main --user alice"
Write-Host "  python -m worker.main --user alice --coordinator-ip localhost --http-port 8081 --ws-port 8080"
Write-Host ""
Pop-Location
