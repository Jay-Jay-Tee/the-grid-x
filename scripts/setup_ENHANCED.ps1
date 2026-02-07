# Grid-X Windows Setup Script - Enhanced Version
# Run with: powershell -ExecutionPolicy Bypass -File setup_ENHANCED.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host " Grid-X Windows Setup - v1.0.0" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Some features may not work correctly" -ForegroundColor Yellow
    Write-Host ""
}

# 1. Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Found: $pythonVersion" -ForegroundColor Green
    
    # Check if version is 3.9+
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
    if ($versionMatch) {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if (($major -lt 3) -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Host "  ⚠️  Python 3.9+ required, found $major.$minor" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  ❌ Python not found!" -ForegroundColor Red
    Write-Host "     Please install Python 3.9+ from https://python.org" -ForegroundColor Red
    exit 1
}

# 2. Check Docker
Write-Host ""
Write-Host "[2/6] Checking Docker..." -ForegroundColor Green
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "  ✓ Found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Docker not found" -ForegroundColor Yellow
    Write-Host "     Workers require Docker Desktop for Windows" -ForegroundColor Yellow
    Write-Host "     Download from: https://docker.com/products/docker-desktop" -ForegroundColor Yellow
}

# 3. Create virtual environment
Write-Host ""
Write-Host "[3/6] Creating Python virtual environment..." -ForegroundColor Green
if (Test-Path "venv") {
    Write-Host "  ℹ️  Virtual environment already exists" -ForegroundColor Cyan
} else {
    python -m venv venv
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
}

# 4. Activate and install dependencies
Write-Host ""
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Green
& "venv\Scripts\Activate.ps1"

# Upgrade pip
python -m pip install --upgrade pip --quiet

# Install coordinator dependencies
if (Test-Path "coordinator\requirements.txt") {
    Write-Host "  → Installing coordinator dependencies..." -ForegroundColor Cyan
    pip install -r coordinator\requirements.txt --quiet
    Write-Host "  ✓ Coordinator dependencies installed" -ForegroundColor Green
}

# Install worker dependencies
if (Test-Path "worker\requirements.txt") {
    Write-Host "  → Installing worker dependencies..." -ForegroundColor Cyan
    pip install -r worker\requirements.txt --quiet
    Write-Host "  ✓ Worker dependencies installed" -ForegroundColor Green
}

# 5. Initialize database
Write-Host ""
Write-Host "[5/6] Initializing database..." -ForegroundColor Green
python -c "import sys; sys.path.append('coordinator'); from database import init_db; init_db()"
Write-Host "  ✓ Database initialized" -ForegroundColor Green

# 6. Create necessary directories
Write-Host ""
Write-Host "[6/6] Creating directories..." -ForegroundColor Green
$dirs = @("data", "logs", "workspaces")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  ✓ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ℹ️  Exists: $dir" -ForegroundColor Cyan
    }
}

# Done
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host " Setup Complete! ✨" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start Grid-X:" -ForegroundColor White
Write-Host ""
Write-Host "1. Start Coordinator:" -ForegroundColor Yellow
Write-Host "   cd coordinator" -ForegroundColor Gray
Write-Host "   python -m coordinator.main" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start Worker (in new terminal):" -ForegroundColor Yellow
Write-Host "   cd worker" -ForegroundColor Gray
Write-Host "   python -m worker.main --user alice --password password123" -ForegroundColor Gray
Write-Host ""
Write-Host "For more information, see README.md and SETUP.md" -ForegroundColor White
Write-Host ""
