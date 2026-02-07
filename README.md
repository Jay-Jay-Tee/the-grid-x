# GRID‑X

Lightweight coordinator + worker codebase for distributed Python task execution.

Status: development — actively maintained. This README focuses on quick, reproducible local development and running the main components.

## What is it
Coordinator (server) assigns jobs and tracks workers. Workers execute user tasks (Docker recommended).

Core components:
- `coordinator/` — FastAPI HTTP + WebSocket server
- `worker/` — Worker agent, task execution, and Docker helpers
- `worker_app/` — Optional local GUI for worker management
- `sdk/` — TypeScript client SDK

## Prerequisites
- Python 3.9+
- Docker (for running jobs inside containers)

## Quickstart — Local development

1. Create a venv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Start the coordinator (default ports 8081 HTTP, 8080 WS):

```powershell
python -m coordinator.main
```

# GRID‑X

Lightweight coordinator + worker repository for distributed Python task execution.

Status: development — focused on reproducible local development and small deployments.

## Overview
The repository contains:

- `coordinator/` — FastAPI HTTP + WebSocket server (scheduler, APIs)
- `worker/` — Worker agent and execution helpers (Docker-backed execution)
- `worker_app/` — Optional desktop GUI for local workers
- `sdk/` — TypeScript client SDK for external integrations

See [FILEDIR.md](FILEDIR.md) for a compact project map.

## Prerequisites

- Python 3.9+
- Docker (recommended for executing jobs in isolation)

## Local development quickstart (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies (top-level + components):

```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install -r coordinator\requirements.txt
pip install -r worker\requirements.txt
pip install -r worker_app\requirements.txt  # optional GUI
```

Alternatively run the setup script:

```powershell
.\scripts\setup.ps1
```

3. Start the coordinator (defaults: HTTP 8081, WS 8080):

```powershell
python -m coordinator.main
```

4. Start a worker (point to coordinator host/IP):

```powershell
python -m worker.main --user <name> --password <pw> --coordinator-ip 127.0.0.1
```

5. (Optional) Start the worker GUI:

```powershell
python -m worker_app.main
```

## Running workers in Docker (example)

```powershell
docker build -t gridx-worker:dev -f worker/Dockerfile .
docker run --rm -e COORDINATOR_HTTP=http://host:8081 gridx-worker:dev
```

## Configuration

Use `config/` and `env.example` as a starting point. Common env vars:

```text
GRIDX_HTTP_PORT=8081
GRIDX_WS_PORT=8080
GRIDX_DB_PATH=./data/gridx.db
COORDINATOR_HTTP=http://127.0.0.1:8081
COORDINATOR_WS=ws://127.0.0.1:8080/ws/worker
```

## Tests

Run unit tests with pytest:

```powershell
pip install -r requirements.txt
pytest -q
```

## Contributing

- Open issues or PRs. Keep changes small and add unit tests for new logic.
- Consider adding `pyproject.toml` and `pre-commit` for consistent formatting.

## License & Authors

Authors: Joshua, Sidharth, Ujjwal, Soorya
License: see `LICENSE` at repo root.

---
Updated: February 2026
