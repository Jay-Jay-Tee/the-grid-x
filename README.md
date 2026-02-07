# Grid-X: Distributed Compute Network

A decentralized computing network where users can earn credits by sharing computational resources and spend those credits to run jobs on other machines. Built with FastAPI, WebSockets, and Docker for secure, sandboxed execution.

## Overview

Grid-X is a peer-to-peer compute platform that enables:

- **Run Code Anywhere**: Submit Python code to execute on idle machines in the network
- **Earn Credits**: Share your computing power and earn credits when others use your resources
- **Credit-Based Economy**: Built-in credit system balances supply and demand for compute resources
- **Secure Execution**: All jobs run in isolated Docker containers with resource limits
- **Real-Time Monitoring**: Dashboard and WebSocket API for live job tracking and resource monitoring

## Architecture

Grid-X consists of three main components:

### 1. **Coordinator** (Central Server)
- Single instance that orchestrates the entire network
- Manages job queue and worker assignments
- Tracks credit balances and transactions
- Real-time WebSocket server for worker communication
- HTTP REST API for job submission and status

### 2. **Workers** (Compute Nodes)
- Multiple instances that connect to the coordinator
- Monitor local system resources (CPU, GPU, memory)
- Accept and execute assigned jobs in Docker containers
- Report job results back to coordinator
- Earn credits based on computation completed

### 3. **SDK & UI**
- **TypeScript SDK**: Client library for integrating Grid-X into applications
- **React Dashboard**: Web UI for job submission, monitoring, and credit management

## Quick Start

### Prerequisites
- Python 3.9+
- Docker and Docker Daemon running
- Docker Compose (optional, for multi-container setup)

### Installation with Setup Scripts

The easiest way to get started is using the provided setup scripts, which automatically handle all prerequisites, dependencies, and initialization.

#### Coordinator Setup

**Linux/macOS:**
```bash
bash scripts/setup.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

This will:
- ✓ Check Python, pip, Docker prerequisites
- ✓ Create and activate virtual environment
- ✓ Install all dependencies
- ✓ Initialize the SQLite database
- ✓ Start the coordinator server
- Coordinator API: `http://localhost:8081`
- WebSocket: `ws://localhost:8080`

#### Worker Setup

Run from a different terminal (after coordinator is running):

**Linux/macOS:**
```bash
bash worker/setup.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File worker/setup.ps1
```

You'll be prompted to enter:
- Your user ID (to earn credits with)
- Coordinator IP/hostname (default: localhost)
- Coordinator ports (default: 8081 for HTTP, 8080 for WebSocket)

### Manual Installation

Alternatively, you can run components manually:

1. **Clone and setup**
   ```bash
   cd Grid-X
   pip install -r requirements.txt
   ```

2. **Run Coordinator**
   ```bash
   python -m coordinator.main
   ```
   - HTTP API available at `http://localhost:8081`
   - WebSocket available at `ws://localhost:8080`

3. **Run Worker**
   ```bash
   python -m worker.main --user alice
   ```
   - Connects to coordinator
   - Starts executing jobs
   - Earns credits

### Docker Setup

Run the full stack with Docker Compose:

```bash
docker-compose up
```

For development:
```bash
docker-compose -f docker-compose.dev.yml up
```

## Usage

### Submit a Job (as User)

```python
import requests

response = requests.post(
    "http://localhost:8081/jobs",
    json={
        "user_id": "alice",
        "code": "print('Hello from Grid-X!')",
        "language": "python"
    }
)
job_id = response.json()["job_id"]

# Check status
result = requests.get(f"http://localhost:8081/jobs/{job_id}")
print(result.json())
```

### Run a Worker

```bash
python -m worker.main --user bob
```

The worker will:
1. Connect to coordinator
2. Report system capabilities (CPU cores, GPU availability)
3. Wait for job assignments
4. Execute jobs in Docker containers
5. Send results back to coordinator
6. Earn credits (default: 0.8 credits per job)

### TypeScript SDK

```typescript
import { GridXClient } from "@grid-x/sdk";

const client = new GridXClient({
  coordinatorUrl: "http://localhost:8081",
  wsUrl: "ws://localhost:8080"
});

const jobId = await client.submitJob({
  userId: "alice",
  code: "print('Hello')",
  language: "python"
});

const result = await client.getJob(jobId);
```

## Configuration

Environment variables in `.env`:

```env
# Coordinator
GRIDX_DB_PATH=gridx.db
GRIDX_INITIAL_CREDITS=100.0
GRIDX_JOB_COST=1.0
GRIDX_WORKER_REWARD=0.8
COORDINATOR_HTTP_PORT=8081
COORDINATOR_WS_PORT=8080

# Worker
GRIDX_DOCKER_SOCKET=/var/run/docker.sock
COORDINATOR_IP=localhost
WORKER_USER_ID=worker-1
```

## Credit System

- **New Users**: Start with 100 credits
- **Job Submission Cost**: 1 credit per job (configurable)
- **Worker Reward**: 0.8 credits when your worker runs a job
- **System Design**: Credits ensure fair resource allocation

## API Endpoints

### Jobs

- `POST /jobs` - Submit a new job
- `GET /jobs/{job_id}` - Get job status and results

### Workers

- `POST /workers/register` - Register a worker (HTTP)
- `GET /workers` - List all workers
- `POST /workers/{worker_id}/heartbeat` - Worker heartbeat

### WebSocket

- `ws://localhost:8080/ws/worker` - Worker connection for real-time updates

## Project Structure

```
Grid-X/
├── coordinator/          # Central server
├── worker/              # Worker agents
├── sdk/                 # TypeScript client SDK
├── ui/                  # React dashboard
├── common/              # Shared utilities
├── config/              # Configuration files
├── tests/               # Test suite
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## Development

### Run Tests

```bash
python -m pytest tests/
```

### Integration Tests

```bash
bash scripts/test-integration.sh
```

### Development Server

```bash
bash scripts/start-dev.sh
```

## Documentation

- [API Reference](docs/api-reference.md) - Detailed API documentation
- [Architecture](docs/architecture.md) - System design and data flow
- [Deployment](docs/deployment.md) - Production deployment guide
- [Security](docs/security.md) - Security considerations and best practices

## Features

- ✅ Distributed compute network
- ✅ Credit-based economy
- ✅ Docker-based job isolation
- ✅ Real-time WebSocket communication
- ✅ Resource monitoring (CPU, GPU, memory)
- ✅ Web dashboard
- ✅ TypeScript SDK
- ✅ REST API
- 🔄 Multiple language support (Python currently)
- 🔄 GPU support
- 🔄 Advanced scheduling

## License

See [LICENSE](LICENSE) file for details.

## Contributors

- Siddharth
- Joshua
- Ujjwal
- Soorya Dev
