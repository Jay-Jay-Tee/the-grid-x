# Grid-X Worker Setup Script (Windows PowerShell) - Enhanced Version
# 
# This script:
# 1. Checks prerequisites (Python 3.9+, Docker, pip)
# 2. Creates and activates a Python virtual environment
# 3. Installs Python dependencies
# 4. Validates configuration
# 5. Starts the worker with proper authentication
#
# Version: 1.0.0 (Fixed Release)

#Requires -Version 5.0

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Blue = "Cyan"
$Gray = "Gray"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "============================================================" -ForegroundColor $Blue
Write-Host " Grid-X Worker Setup - Enhanced Version 1.0.0" -ForegroundColor $Blue
Write-Host "============================================================" -ForegroundColor $Blue
Write-Host ""

###############################################################################
# Check if Running as Administrator
###############################################################################

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "✓ Running as Administrator" -ForegroundColor $Green
} else {
    Write-Host "⚠️  Not running as Administrator" -ForegroundColor $Yellow
    Write-Host "   Some Docker features may require admin privileges" -ForegroundColor $Yellow
}
Write-Host ""

###############################################################################
# Check Prerequisites
###############################################################################

Write-Host "[1/6] Checking prerequisites..." -ForegroundColor $Green
Write-Host ""

# Check Python
try {
    $PythonVersion = python --version 2>&1
    Write-Host "  ✓ Found: $PythonVersion" -ForegroundColor $Green
    
    # Check if version is 3.9+
    if ($PythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if (($major -lt 3) -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Host "  ⚠️  Python 3.9+ required, found $major.$minor" -ForegroundColor $Yellow
            Write-Host "     Download from: https://www.python.org/" -ForegroundColor $Yellow
            exit 1
        } else {
            Write-Host "  ✓ Version check passed ($major.$minor >= 3.9)" -ForegroundColor $Green
        }
    }
} catch {
    Write-Host "  ✗ Python is not installed or not in PATH" -ForegroundColor $Red
    Write-Host "     Please install Python 3.9+ from https://www.python.org/" -ForegroundColor $Red
    Write-Host "     Make sure to check 'Add Python to PATH' during installation" -ForegroundColor $Red
    exit 1
}

# Check pip
try {
    $PipVersion = pip --version 2>&1
    Write-Host "  ✓ pip found: $PipVersion" -ForegroundColor $Green
} catch {
    Write-Host "  ✗ pip is not installed" -ForegroundColor $Red
    Write-Host "     Run: python -m ensurepip" -ForegroundColor $Red
    exit 1
}

# Check Docker
try {
    $DockerVersion = docker --version 2>&1
    Write-Host "  ✓ Docker found: $DockerVersion" -ForegroundColor $Green
} catch {
    Write-Host "  ✗ Docker is not installed or not in PATH" -ForegroundColor $Red
    Write-Host "     Please install Docker Desktop from https://docs.docker.com/desktop/" -ForegroundColor $Red
    Write-Host "     Workers require Docker to execute jobs securely" -ForegroundColor $Red
    exit 1
}

# Check Docker daemon
try {
    docker ps > $null 2>&1
    Write-Host "  ✓ Docker daemon is running" -ForegroundColor $Green
} catch {
    Write-Host "  ✗ Docker daemon is not running" -ForegroundColor $Red
    Write-Host "     Please start Docker Desktop" -ForegroundColor $Red
    exit 1
}

Write-Host ""

###############################################################################
# Create Virtual Environment
###############################################################################

Write-Host "[2/6] Setting up Python virtual environment..." -ForegroundColor $Green
$VenvPath = Join-Path $ProjectRoot "venv"

if (Test-Path $VenvPath) {
    Write-Host "  ℹ️  Virtual environment already exists" -ForegroundColor $Blue
} else {
    Write-Host "  → Creating virtual environment..." -ForegroundColor $Gray
    python -m venv $VenvPath
    Write-Host "  ✓ Virtual environment created" -ForegroundColor $Green
}

# Activate virtual environment
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
    Write-Host "  ✓ Virtual environment activated" -ForegroundColor $Green
} else {
    Write-Host "  ✗ Cannot find activation script" -ForegroundColor $Red
    exit 1
}
Write-Host ""

###############################################################################
# Install Dependencies
###############################################################################

Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor $Green
Write-Host ""

# Upgrade pip
Write-Host "  → Upgrading pip..." -ForegroundColor $Gray
python -m pip install --quiet --upgrade pip setuptools wheel
Write-Host "pip upgraded" -ForegroundColor Green

if (Test-Path "worker\requirements.txt") {
    pip install --quiet -r worker\requirements.txt
    Write-Host "Worker dependencies installed" -ForegroundColor Green
}

Write-Host ""

###############################################################################
# Create Required Directories
###############################################################################

Write-Host "[4/6] Creating required directories..." -ForegroundColor $Green

$directories = @(
    (Join-Path $ProjectRoot "data"),
    (Join-Path $ProjectRoot "logs"),
    (Join-Path $ProjectRoot "workspaces")
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "  ✓ Created: $dir" -ForegroundColor $Green
    } else {
        Write-Host "  ℹ️  Exists: $dir" -ForegroundColor $Blue
    }
}

Write-Host ""

###############################################################################
# Worker Configuration
###############################################################################

Write-Host "[5/6] Worker Configuration" -ForegroundColor $Green
Write-Host ""

# User ID (required)
do {
    $UserId = Read-Host "  Enter your user ID (for credit tracking)"
    if ([string]::IsNullOrWhiteSpace($UserId)) {
        Write-Host "  ✗ User ID is required" -ForegroundColor $Red
    } elseif ($UserId -notmatch '^[a-zA-Z0-9_-]+$') {
        Write-Host "  ✗ User ID can only contain letters, numbers, underscore, and hyphen" -ForegroundColor $Red
        $UserId = $null
    } elseif ($UserId.Length -gt 64) {
        Write-Host "  ✗ User ID must be 64 characters or less" -ForegroundColor $Red
        $UserId = $null
    }
} while ([string]::IsNullOrWhiteSpace($UserId))

# Password (required) - FIXED: Now properly asks for password
do {
    $PasswordSecure = Read-Host "  Enter your password" -AsSecureString
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($PasswordSecure)
    )
    
    if ([string]::IsNullOrWhiteSpace($Password)) {
        Write-Host "  ✗ Password is required" -ForegroundColor $Red
    } elseif ($Password.Length -lt 8) {
        Write-Host "  ✗ Password must be at least 8 characters" -ForegroundColor $Red
        $Password = $null
    } elseif ($Password.Length -gt 128) {
        Write-Host "  ✗ Password must be 128 characters or less" -ForegroundColor $Red
        $Password = $null
    }
} while ([string]::IsNullOrWhiteSpace($Password))

Write-Host ""

# Coordinator settings (optional, with defaults)
$CoordinatorIpInput = Read-Host "  Enter coordinator IP/hostname [localhost]"
$CoordinatorIp = if ([string]::IsNullOrWhiteSpace($CoordinatorIpInput)) { "localhost" } else { $CoordinatorIpInput }

$HttpPortInput = Read-Host "  Enter coordinator HTTP port [8081]"
$HttpPort = if ([string]::IsNullOrWhiteSpace($HttpPortInput)) { "8081" } else { $HttpPortInput }

$WsPortInput = Read-Host "  Enter coordinator WebSocket port [8080]"
$WsPort = if ([string]::IsNullOrWhiteSpace($WsPortInput)) { "8080" } else { $WsPortInput }

Write-Host ""

###############################################################################
# Verify Coordinator Connection
###############################################################################

Write-Host "[6/6] Verifying coordinator connection..." -ForegroundColor $Green

$coordinatorUrl = "http://${CoordinatorIp}:${HttpPort}/health"
try {
    $healthCheck = Invoke-WebRequest -Uri $coordinatorUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "  ✓ Coordinator is reachable at $coordinatorUrl" -ForegroundColor $Green
    }
} catch {
    Write-Host "  ⚠️  Cannot reach coordinator at $coordinatorUrl" -ForegroundColor $Yellow
    Write-Host "     Make sure the coordinator is running before starting the worker" -ForegroundColor $Yellow
}

Write-Host ""

###############################################################################
# Display Configuration Summary
###############################################################################

Write-Host "============================================================" -ForegroundColor $Blue
Write-Host " Starting Grid-X Worker" -ForegroundColor $Blue
Write-Host "============================================================" -ForegroundColor $Blue
Write-Host ""
Write-Host "Configuration:" -ForegroundColor $Blue
Write-Host "  User ID:          $UserId" -ForegroundColor $Gray
Write-Host "  Password:         ********" -ForegroundColor $Gray
Write-Host "  Coordinator:      $CoordinatorIp" -ForegroundColor $Gray
Write-Host "  HTTP Port:        $HttpPort" -ForegroundColor $Gray
Write-Host "  WebSocket Port:   $WsPort" -ForegroundColor $Gray
Write-Host "  WebSocket URL:    ws://${CoordinatorIp}:${WsPort}/ws/worker" -ForegroundColor $Gray
Write-Host ""
Write-Host "Controls:" -ForegroundColor $Blue
Write-Host "  Press Ctrl+C to stop the worker" -ForegroundColor $Yellow
Write-Host ""
