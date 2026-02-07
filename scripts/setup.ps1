# Grid-X Coordinator Setup Script (Windows PowerShell)
# 
# This script:
# 1. Checks prerequisites (Python, Docker, pip)
# 2. Creates and activates a Python virtual environment
# 3. Installs Python dependencies
# 4. Initializes the database
# 5. Starts the coordinator server

#Requires -Version 5.0

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Grid-X Coordinator Setup ===" -ForegroundColor $Green
Write-Host ""

###############################################################################
# Check Prerequisites
###############################################################################

Write-Host "Checking prerequisites..." -ForegroundColor $Yellow

# Check Python
try {
    $PythonVersion = python --version 2>&1
    Write-Host "✓ $PythonVersion found" -ForegroundColor $Green
} catch {
    Write-Host "✗ Python is not installed or not in PATH" -ForegroundColor $Red
    Write-Host "  Please install Python 3.9+ from https://www.python.org/" -ForegroundColor $Red
    Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor $Red
    exit 1
}

# Check pip
try {
    $PipVersion = pip --version 2>&1
    Write-Host "✓ pip found" -ForegroundColor $Green
} catch {
    Write-Host "✗ pip is not installed" -ForegroundColor $Red
    Write-Host "  Run: python -m ensurepip" -ForegroundColor $Red
    exit 1
}

# Check Docker
try {
    $DockerVersion = docker --version 2>&1
    Write-Host "✓ Docker found: $DockerVersion" -ForegroundColor $Green
} catch {
    Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor $Red
    Write-Host "  Please install Docker Desktop from https://docs.docker.com/desktop/" -ForegroundColor $Red
    exit 1
}

# Check Docker daemon
try {
    docker ps > $null 2>&1
    Write-Host "✓ Docker daemon is running" -ForegroundColor $Green
} catch {
    Write-Host "✗ Docker daemon is not running" -ForegroundColor $Red
    Write-Host "  Please start Docker Desktop" -ForegroundColor $Red
    exit 1
}

Write-Host ""

###############################################################################
# Create Virtual Environment
###############################################################################

Write-Host "Setting up Python virtual environment..." -ForegroundColor $Yellow
$VenvPath = Join-Path $ProjectRoot "venv"

if (Test-Path $VenvPath) {
    Write-Host "  Virtual environment already exists at $VenvPath"
} else {
    python -m venv $VenvPath
    Write-Host "✓ Virtual environment created" -ForegroundColor $Green
}

# Activate virtual environment
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
& $ActivateScript
Write-Host "✓ Virtual environment activated" -ForegroundColor $Green
Write-Host ""

###############################################################################
# Install Dependencies
###############################################################################

Write-Host "Installing Python dependencies..." -ForegroundColor $Yellow

# Upgrade pip
python -m pip install --quiet --upgrade pip setuptools wheel

# Install coordinator requirements
$CoordinatorReqs = Join-Path $ProjectRoot "coordinator\requirements.txt"
if (Test-Path $CoordinatorReqs) {
    pip install --quiet -r $CoordinatorReqs
    Write-Host "✓ Coordinator dependencies installed" -ForegroundColor $Green
} else {
    Write-Host "✗ Cannot find coordinator/requirements.txt" -ForegroundColor $Red
    exit 1
}

# Install root requirements if they exist
$RootReqs = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $RootReqs) {
    pip install --quiet -r $RootReqs
    Write-Host "✓ Common dependencies installed" -ForegroundColor $Green
}

Write-Host ""

###############################################################################
# Setup Environment Variables
###############################################################################

Write-Host "Setting up environment..." -ForegroundColor $Yellow

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "✓ Created .env from .env.example" -ForegroundColor $Green
}

Write-Host ""

###############################################################################
# Initialize Database
###############################################################################

Write-Host "Initializing database..." -ForegroundColor $Yellow

Push-Location $ProjectRoot

$PyScript = @"
import sys
sys.path.insert(0, '.')
from coordinator.database import db_init
db_init()
print('✓ Database initialized')
"@

python -c $PyScript

Pop-Location

Write-Host ""

###############################################################################
# Start Coordinator
###############################################################################

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
