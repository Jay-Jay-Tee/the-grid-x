#!/bin/bash

###############################################################################
# Grid-X Coordinator Setup Script (Linux/macOS)
# 
# This script:
# 1. Checks prerequisites (Python, Docker, pip)
# 2. Creates and activates a Python virtual environment
# 3. Installs Python dependencies
# 4. Initializes the database
# 5. Starts the coordinator server
###############################################################################

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}=== Grid-X Coordinator Setup ===${NC}\n"

###############################################################################
# Check Prerequisites
###############################################################################

echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo "  Please install Python 3.9 or higher from https://www.python.org/"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✗ pip3 is not installed${NC}"
    echo "  Please install pip: python3 -m ensurepip"
    exit 1
fi
echo -e "${GREEN}✓ pip3 found${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "  Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker daemon
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "  Please start the Docker daemon"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}\n"

###############################################################################
# Create Virtual Environment
###############################################################################

echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
VENV_PATH="$PROJECT_ROOT/venv"

if [ -d "$VENV_PATH" ]; then
    echo -e "  Virtual environment already exists at $VENV_PATH"
else
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

###############################################################################
# Install Dependencies
###############################################################################

echo -e "${YELLOW}Installing Python dependencies...${NC}"

# Upgrade pip
pip install --quiet --upgrade pip setuptools wheel

# Install coordinator requirements
if [ -f "$PROJECT_ROOT/coordinator/requirements.txt" ]; then
    pip install --quiet -r "$PROJECT_ROOT/coordinator/requirements.txt"
    echo -e "${GREEN}✓ Coordinator dependencies installed${NC}"
else
    echo -e "${RED}✗ Cannot find coordinator/requirements.txt${NC}"
    exit 1
fi

# Install common dependencies if they exist
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    pip install --quiet -r "$PROJECT_ROOT/requirements.txt"
    echo -e "${GREEN}✓ Common dependencies installed${NC}"
fi

echo ""

###############################################################################
# Setup Environment Variables
###############################################################################

echo -e "${YELLOW}Setting up environment...${NC}"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
    fi
fi

echo ""

###############################################################################
# Initialize Database (clean + create fresh)
###############################################################################

echo -e "${YELLOW}Initializing database (cleaning existing gridx.db and creating fresh)...${NC}"

cd "$PROJECT_ROOT"
python3 << 'EOF'
import sys
import os
sys.path.insert(0, '.')

# Load .env so GRIDX_DB_PATH is respected
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

db_path = os.getenv("GRIDX_DB_PATH", "./data/gridx.db")
if not os.path.isabs(db_path):
    db_path = os.path.normpath(os.path.join(os.getcwd(), db_path))

if os.path.isfile(db_path):
    os.remove(db_path)
    print("✓ Removed existing database")

db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

from coordinator.database import db_init
db_init()
print("✓ Database initialized (fresh)")
EOF

echo ""

###############################################################################
# Start Coordinator
###############################################################################

echo -e "${GREEN}=== Starting Grid-X Coordinator ===${NC}\n"
echo "Coordinator HTTP API: http://localhost:8081"
echo "WebSocket Server: ws://localhost:8080"
echo ""
echo "API Docs: http://localhost:8081/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}\n"

cd "$PROJECT_ROOT"
python3 -m coordinator.main
