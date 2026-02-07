#!/bin/bash

###############################################################################
# Grid-X Worker Setup Script (Linux/macOS)
# 
# This script:
# 1. Checks prerequisites (Python, Docker, pip)
# 2. Creates and activates a Python virtual environment
# 3. Installs Python dependencies
# 4. Starts the worker
###############################################################################

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}=== Grid-X Worker Setup ===${NC}\n"

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

# Install worker requirements
if [ -f "$PROJECT_ROOT/worker/requirements.txt" ]; then
    pip install --quiet -r "$PROJECT_ROOT/worker/requirements.txt"
    echo -e "${GREEN}✓ Worker dependencies installed${NC}"
else
    echo -e "${RED}✗ Cannot find worker/requirements.txt${NC}"
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
# Get User ID
###############################################################################

echo -e "${BLUE}Worker Configuration:${NC}"
read -p "Enter your user ID (name to earn credits with): " USER_ID

if [ -z "$USER_ID" ]; then
    echo -e "${RED}Error: User ID is required${NC}"
    exit 1
fi

read -p "Enter coordinator IP/hostname [localhost]: " COORDINATOR_IP
COORDINATOR_IP=${COORDINATOR_IP:-localhost}

read -p "Enter coordinator HTTP port [8081]: " HTTP_PORT
HTTP_PORT=${HTTP_PORT:-8081}

read -p "Enter coordinator WebSocket port [8080]: " WS_PORT
WS_PORT=${WS_PORT:-8080}

echo ""

###############################################################################
# Start Worker
###############################################################################

echo -e "${GREEN}=== Starting Grid-X Worker ===${NC}\n"
echo -e "${BLUE}Configuration:${NC}"
echo "  User ID: $USER_ID"
echo "  Coordinator: $COORDINATOR_IP"
echo "  HTTP Port: $HTTP_PORT"
echo "  WebSocket Port: $WS_PORT"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the worker${NC}\n"

cd "$PROJECT_ROOT"
python3 -m worker.main --user "$USER_ID" --coordinator-ip "$COORDINATOR_IP" --http-port "$HTTP_PORT" --ws-port "$WS_PORT"
