# Grid-X Coordinator Setup Script (Windows PowerShell)
# This script initializes the Grid-X coordinator environment and starts the server

#Requires -Version 5.0
$ErrorActionPreference = "Stop"

$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Grid-X Coordinator Setup ===" -ForegroundColor $Green
Write-Host ""

# Check Prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor $Yellow

$PythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ $PythonVersion found" -ForegroundColor $Green
} else {
    Write-Host "✗ Python is not installed or not in PATH" -ForegroundColor $Red
    exit 1
}

$PipVersion = pip --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ pip found" -ForegroundColor $Green
} else {
    Write-Host "✗ pip is not installed" -ForegroundColor $Red
    exit 1
}

$DockerVersion = docker --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker found: $DockerVersion" -ForegroundColor $Green
} else {
    Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor $Red
    exit 1
}

docker ps > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker daemon is running" -ForegroundColor $Green
} else {
    Write-Host "✗ Docker daemon is not running" -ForegroundColor $Red
    exit 1
}

Write-Host ""
Write-Host "Setting up Python virtual environment..." -ForegroundColor $Yellow

$VenvPath = Join-Path $ProjectRoot "venv"

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
    Write-Host "✓ Virtual environment created" -ForegroundColor $Green
} else {
    Write-Host "✓ Virtual environment already exists at $VenvPath" -ForegroundColor $Green
}

$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
& $ActivateScript
Write-Host "✓ Virtual environment activated" -ForegroundColor $Green
Write-Host ""

# Install Dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor $Yellow

python -m pip install --quiet --upgrade pip setuptools wheel

$CoordinatorReqs = Join-Path $ProjectRoot "coordinator\requirements.txt"
if (Test-Path $CoordinatorReqs) {
    pip install --quiet -r $CoordinatorReqs
    Write-Host "✓ Coordinator dependencies installed" -ForegroundColor $Green
} else {
    Write-Host "✗ Cannot find coordinator/requirements.txt" -ForegroundColor $Red
    exit 1
}

$RootReqs = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $RootReqs) {
    pip install --quiet -r $RootReqs
    Write-Host "✓ Common dependencies installed" -ForegroundColor $Green
}

Write-Host ""
Write-Host "Setting up environment..." -ForegroundColor $Yellow

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if ((-not (Test-Path $EnvFile)) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "✓ Created .env from .env.example" -ForegroundColor $Green
}

Write-Host ""
Write-Host "Initializing database..." -ForegroundColor $Yellow

Push-Location $ProjectRoot
python -c "import sys; sys.path.insert(0, '.'); from coordinator.database import db_init; db_init()"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Database initialization failed" -ForegroundColor $Red
    exit 1
}
Write-Host "✓ Database initialized" -ForegroundColor $Green
Pop-Location

Write-Host ""
Write-Host "=== Starting Grid-X Coordinator ===" -ForegroundColor $Green
Write-Host ""
Write-Host "Coordinator HTTP API: http://localhost:8081"
Write-Host "WebSocket Server: ws://localhost:8080"
Write-Host ""
Write-Host "API Docs: http://localhost:8081/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor $Yellow
Write-Host ""

Push-Location $ProjectRoot
python -m coordinator.main
Pop-Location
