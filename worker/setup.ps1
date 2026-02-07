# Grid-X Worker Setup Script (Windows PowerShell)

$ErrorActionPreference = "Stop"

# Get project root directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Push-Location $ProjectRoot

Write-Host "=== Grid-X Worker Setup ===" -ForegroundColor Green
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Cyan
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
    pip --version | Out-Null
    Write-Host "pip found" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: pip not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow

$VenvPath = Join-Path $ProjectRoot "venv"
if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
    Write-Host "Virtual environment created" -ForegroundColor Green
}
else {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
}

$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
& $ActivateScript
Write-Host "Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Install Dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow

python -m pip install --upgrade pip setuptools wheel
Write-Host "pip upgraded" -ForegroundColor Green
Write-Host ""

# Install coordinator requirements
$CoordinatorReqs = Join-Path $ProjectRoot "coordinator\requirements.txt"
if (Test-Path $CoordinatorReqs) {
    Write-Host "Installing coordinator dependencies from: $CoordinatorReqs" -ForegroundColor Cyan
    pip install -r $CoordinatorReqs
    Write-Host "Coordinator dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "WARNING: coordinator\requirements.txt not found at $CoordinatorReqs" -ForegroundColor Yellow
}
Write-Host ""

# Install worker requirements
$WorkerReqs = Join-Path $ProjectRoot "worker\requirements.txt"
if (Test-Path $WorkerReqs) {
    Write-Host "Installing worker dependencies from: $WorkerReqs" -ForegroundColor Cyan
    pip install -r $WorkerReqs
    Write-Host "Worker dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "WARNING: worker\requirements.txt not found at $WorkerReqs" -ForegroundColor Yellow
}
Write-Host ""

# Install root requirements
$RootReqs = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $RootReqs) {
    Write-Host "Installing common dependencies from: $RootReqs" -ForegroundColor Cyan
    pip install -r $RootReqs
    Write-Host "Common dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "INFO: requirements.txt not found at $RootReqs" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the worker, use one of these commands:" -ForegroundColor Cyan
Write-Host "  python -m worker.main --user alice --password yourpassword" -ForegroundColor White
Write-Host ""
Write-Host "  (With custom coordinator settings:)" -ForegroundColor Cyan
Write-Host "  python -m worker.main --user alice --password yourpassword --coordinator-ip localhost --http-port 8081 --ws-port 8080" -ForegroundColor White
Write-Host ""

Pop-Location
