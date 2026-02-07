# Grid-X Setup Guide

## Prerequisites

1. **System Requirements**
   - Linux/MacOS/Windows with WSL2
   - 4GB+ RAM
   - 10GB+ disk space
   - Docker installed and running

2. **Software Dependencies**
   - Python 3.9 or higher
   - pip (Python package manager)
   - Docker 20.10 or higher
   - (Optional) Node.js 18+ for web UI

## Installation Steps

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd grid-x
```

### 2. Install Python Dependencies

```bash
# For coordinator
cd coordinator
pip install -r requirements.txt

# For worker
cd ../worker
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
cd coordinator
python -c "from database import init_db; init_db()"
```

### 4. Configure Environment

Create a `.env` file in the coordinator directory:

```bash
GRIDX_HTTP_PORT=8081
GRIDX_WS_PORT=8080
GRIDX_DB_PATH=./data/gridx.db
GRIDX_LOG_LEVEL=INFO
```

Create a `.env` file in the worker directory:

```bash
COORDINATOR_WS=ws://localhost:8080/ws/worker
WORKER_USER=your_username
WORKER_PASSWORD=your_password
```

### 5. Start Services

**Terminal 1 - Coordinator:**
```bash
cd coordinator
python -m coordinator.main
```

**Terminal 2 - Worker:**
```bash
cd worker
python -m worker.main --user alice --password password123
```

### 6. Verify Installation

```bash
curl http://localhost:8081/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "grid-x-coordinator",
  "timestamp": 1234567890.123
}
```

## Troubleshooting

### Issue: Authentication Failed
- Verify credentials match on coordinator and worker
- Check network connectivity between coordinator and worker
- Review coordinator logs for authentication attempts

### Issue: Docker Permission Denied
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Port Already in Use
Change ports in .env file or stop conflicting services

## Next Steps

- Read [Architecture Overview](docs/architecture.md)
- Check [API Reference](docs/api-reference.md)
- Review [Security Guide](docs/security.md)
