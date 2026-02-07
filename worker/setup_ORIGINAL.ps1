# Grid-X Worker Setup Script (Windows PowerShell)
# 
# This script:
# 1. Checks prerequisites (Python, Docker, pip)
# 2. Creates and activates a Python virtual environment
# 3. Installs Python dependencies
# 4. Starts the worker

#Requires -Version 5.0

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Blue = "Cyan"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Grid-X Worker Setup ===" -ForegroundColor $Green
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

# Install worker requirements
$WorkerReqs = Join-Path $ProjectRoot "worker\requirements.txt"
if (Test-Path $WorkerReqs) {
    pip install --quiet -r $WorkerReqs
    Write-Host "✓ Worker dependencies installed" -ForegroundColor $Green
} else {
    Write-Host "✗ Cannot find worker/requirements.txt" -ForegroundColor $Red
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
# Get User ID
###############################################################################

Write-Host "Worker Configuration:" -ForegroundColor $Blue

$UserId = Read-Host "Enter your user ID (name to earn credits with)"

if ([string]::IsNullOrEmpty($UserId)) {
    Write-Host "Error: User ID is required" -ForegroundColor $Red
    exit 1
}

$CoordinatorIpInput = Read-Host "Enter coordinator IP/hostname [localhost]"
$CoordinatorIp = if ([string]::IsNullOrEmpty($CoordinatorIpInput)) { "localhost" } else { $CoordinatorIpInput }

$HttpPortInput = Read-Host "Enter coordinator HTTP port [8081]"
$HttpPort = if ([string]::IsNullOrEmpty($HttpPortInput)) { "8081" } else { $HttpPortInput }

$WsPortInput = Read-Host "Enter coordinator WebSocket port [8080]"
$WsPort = if ([string]::IsNullOrEmpty($WsPortInput)) { "8080" } else { $WsPortInput }

Write-Host ""

###############################################################################
# Start Worker
###############################################################################

Write-Host "=== Starting Grid-X Worker ===" -ForegroundColor $Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor $Blue
Write-Host "  User ID: $UserId"
Write-Host "  Coordinator: $CoordinatorIp"
Write-Host "  HTTP Port: $HttpPort"
Write-Host "  WebSocket Port: $WsPort"
Write-Host ""
Write-Host "Press Ctrl+C to stop the worker" -ForegroundColor $Yellow
Write-Host ""

Push-Location $ProjectRoot
python -m worker.main --user $UserId --coordinator-ip $CoordinatorIp --http-port $HttpPort --ws-port $WsPort
