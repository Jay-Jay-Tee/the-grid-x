# Grid-X Coordinator Setup Script
# This script initializes the Grid-X environment on Windows

$ErrorActionPreference = "Stop"

Write-Host "=== Grid-X Setup ===" -ForegroundColor Green
Write-Host ""

# Check Prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$PythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Python found: $PythonVersion" -ForegroundColor Green
}
else {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

try {
    $DockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker found: $DockerVersion" -ForegroundColor Green
    }
}
catch {
    Write-Host "WARNING: Docker not found (optional)" -ForegroundColor Yellow
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
Write-Host "Installing dependencies..." -ForegroundColor Yellow

python -m pip install --quiet --upgrade pip setuptools wheel

if (Test-Path "coordinator\requirements.txt") {
    pip install --quiet -r coordinator\requirements.txt
    Write-Host "Coordinator dependencies installed" -ForegroundColor Green
}

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
Write-Host "To start the coordinator:"
Write-Host "  python -m coordinator.main"
Write-Host ""
Write-Host "To start a worker:"
Write-Host "  python -m worker.main"
Write-Host ""
