# ⚡ Grid-X

**Distributed compute mesh for isolated Python job execution across LAN nodes.**

Submit code. A worker somewhere runs it. You pay in credits; workers earn them.  
One coordinator, unlimited workers, zero shared state between jobs.

---

## What is Grid-X?

Grid-X is a self-hosted distributed task execution network. You deploy one **coordinator** (the brain) and any number of **workers** (the muscle) across machines on your network. Workers register themselves, the coordinator schedules jobs, and every job runs inside an isolated Docker container on whatever worker picks it up.

Credits are time-based: you spend them submitting jobs, workers earn them executing jobs. One coordinator, many workers, clean separation.

```
  Client (you)
      │  POST /jobs  {"code": "...", "user_id": "alice"}
      ▼
  ┌─────────────┐     WebSocket     ┌──────────────┐
  │ Coordinator │ ◄────────────────► │   Worker 1   │  ← Docker container
  │  (FastAPI)  │                   └──────────────┘
  │  HTTP :8081 │ ◄────────────────► ┌──────────────┐
  │  WS   :8080 │                   │   Worker 2   │  ← Docker container
  └─────────────┘                   └──────────────┘
       │
  SQLite DB (jobs, workers, credits)
```

---

## Features

- **Distributed job execution** — Python, JavaScript/Node, and Bash jobs dispatched across workers
- **Docker-isolated sandboxing** — every job runs in a fresh container; workers never share state
- **WebSocket-based coordination** — workers maintain persistent connections; jobs dispatched in real time
- **Time-based credit system** — max reserve at submit, settle on completion, refund unused
- **TypeScript SDK** — submit jobs, poll results, and manage workers programmatically
- **Admin dashboard** — web UI at `/admin` for live worker/job/credit overview
- **Worker GUI** — optional Tkinter desktop app for managing a local worker node
- **Configurable resource limits** — per-job CPU, memory, timeout, and output caps
- **Worker ban/suspend controls** — admin can disconnect or restrict specific workers via API
- **Watchdog scheduler** — stuck jobs are automatically requeued

---

## Architecture

```
coordinator/          Central API + scheduler (FastAPI, single instance)
worker/               Worker agent — connects to coordinator, runs jobs in Docker
worker_app/           Optional desktop GUI for local worker management
sdk/                  TypeScript client SDK
common/               Shared schemas, constants, utils
config/               Environment examples and Docker security config
docs/                 Architecture, API reference, deployment, security notes
tests/                Unit and integration tests
```

The coordinator holds all state (SQLite). Workers are stateless — they register, pull jobs, execute, and report results. A worker can run on any machine that can reach the coordinator's WebSocket port.

---

## Prerequisites

- Python 3.9+
- Docker (required for sandboxed job execution)
- Node.js 18+ (optional — for the TypeScript SDK)

---

## Quickstart

### Option A — Docker Compose (recommended)

Spins up a coordinator + one worker on the same host:

```bash
git clone https://github.com/Jay-Jay-Tee/the-grid-x
cd the-grid-x
docker-compose up --build
```

Coordinator HTTP API will be at `http://localhost:8081`.  
Admin dashboard at `http://localhost:8081/admin`.

### Option B — Local development (Windows PowerShell)

**1. Create and activate a virtual environment:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**2. Install dependencies:**

```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install -r coordinator\requirements.txt
pip install -r worker\requirements.txt
pip install -r worker_app\requirements.txt   # optional GUI
```

**3. Start the coordinator** (HTTP `:8081`, WebSocket `:8080`):

```powershell
python -m coordinator.main
```

**4. Start a worker** (on the same or a different machine):

```powershell
python -m worker.main --user alice --password yourpass --coordinator-ip 127.0.0.1
```

**5. (Optional) Launch the worker desktop GUI:**

```powershell
python -m worker_app.main
```

---

## Multi-Machine Setup

The coordinator and workers can run on separate machines. Set the environment variables on the worker machine:

```bash
COORDINATOR_WS=ws://<COORDINATOR_IP>:8080/ws/worker
WORKER_OWNER_ID=your_user_id
```

Then run:

```bash
python -m worker.main --user alice --password yourpass
```

Or build and run the worker Docker image:

```bash
docker build -t gridx-worker -f worker/Dockerfile .
docker run --rm \
  -e COORDINATOR_WS=ws://<COORDINATOR_IP>:8080/ws/worker \
  -e WORKER_OWNER_ID=alice \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gridx-worker
```

---

## Submitting a Job

**HTTP (curl):**

```bash
curl -X POST http://localhost:8081/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "code": "print(sum(range(1000)))",
    "language": "python"
  }'
```

Response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "reserved": 6.0,
  "message": "Charged by compute time when job completes; unused reserve refunded."
}
```

**Poll for result:**

```bash
curl http://localhost:8081/jobs/550e8400-e29b-41d4-a716-446655440000
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs` | Submit a job |
| `GET` | `/jobs?user_id=alice` | List jobs for a user |
| `GET` | `/jobs/{job_id}` | Get job status and result |
| `GET` | `/workers` | List registered workers |
| `POST` | `/workers/register` | Register a worker via HTTP |
| `POST` | `/workers/{id}/heartbeat` | Worker heartbeat |
| `GET` | `/credits/{user_id}` | Get credit balance |
| `GET` | `/health` | Health check |
| `GET` | `/status` | Coordinator status snapshot |
| `GET` | `/admin` | Admin dashboard UI |
| `GET` | `/admin/overview` | Full admin data snapshot (JSON) |
| `POST` | `/admin/workers/{id}/ban` | Ban a worker |
| `POST` | `/admin/workers/{id}/suspend` | Suspend a worker |
| `POST` | `/admin/workers/{id}/unsuspend` | Unsuspend a worker |
| `POST` | `/admin/workers/{id}/disconnect` | Force-disconnect a worker |
| `POST` | `/admin/broadcast` | Broadcast message to all workers |

### Job submission body

```json
{
  "user_id": "alice",
  "code": "print('hello world')",
  "language": "python",
  "limits": {
    "timeout_s": 60
  }
}
```

Supported languages: `python`, `javascript`, `node`, `bash`.

---

## Credit System

Credits are time-based compute tokens.

- **New users** start with **100.0 credits** (configurable via `GRIDX_INITIAL_CREDITS`)
- At job submission, the **maximum possible cost** is reserved based on the job timeout
- When the job completes, actual compute time is charged; the remainder is **refunded**
- Workers **earn credits** for every second of compute they provide (at 85% of the submitter's cost by default)

| Variable | Default | Description |
|----------|---------|-------------|
| `GRIDX_COST_PER_SECOND` | `0.1` | Credits charged per second of execution |
| `GRIDX_MIN_COST` | `0.05` | Minimum charge per job |
| `GRIDX_MAX_COST` | `25.0` | Maximum charge per job |
| `GRIDX_REWARD_RATIO` | `0.85` | Fraction of cost that goes to the worker owner |
| `GRIDX_INITIAL_CREDITS` | `100.0` | Starting balance for new users |

---

## Configuration

Copy the example env files and adjust as needed:

```bash
cp .env.example .env
cp coordinator/env.example coordinator/.env
cp worker/env.example worker/.env
```

Key variables:

```env
# Coordinator
GRIDX_HTTP_PORT=8081
GRIDX_WS_PORT=8080
GRIDX_DB_PATH=./data/gridx.db

# Worker
COORDINATOR_HTTP=http://127.0.0.1:8081
COORDINATOR_WS=ws://127.0.0.1:8080/ws/worker
WORKER_OWNER_ID=alice
```

---

## TypeScript SDK

Located in `sdk/`. Install and use to interact with the coordinator programmatically:

```bash
cd sdk
npm install
npm run build
```

---

## Running Tests

```powershell
pip install -r requirements.txt
pytest -q
```

Run only coordinator tests:

```powershell
pytest tests/coordinator/ -q
```

Run integration tests (requires coordinator running):

```powershell
pytest tests/integration/ -q
```

---

## Project Structure

```
the-grid-x/
├── coordinator/          # FastAPI coordinator server
│   ├── main.py           # HTTP + WebSocket entrypoint
│   ├── scheduler.py      # Job dispatch + watchdog
│   ├── credit_manager.py # Time-based credit settlement
│   ├── database.py       # SQLite helpers
│   ├── workers.py        # Worker registry
│   ├── websocket.py      # WS server
│   └── admin_ui/         # Admin dashboard HTML
├── worker/               # Worker agent
│   ├── main.py           # CLI entrypoint + WorkerIdentity
│   ├── task_executor.py  # Docker-backed execution
│   ├── docker_manager.py # Container lifecycle
│   ├── resource_monitor.py
│   └── task_queue.py
├── worker_app/           # Optional Tkinter GUI for workers
├── sdk/                  # TypeScript client SDK
├── common/               # Shared schemas, constants, utils
├── config/               # Env examples, docker-security.yml
├── docs/                 # Architecture, API reference, security
├── tests/                # Unit + integration tests
├── scripts/              # Helper scripts
├── docker-compose.yml
└── requirements.txt
```

---

## Security Notes

- Jobs run in isolated Docker containers with configurable resource caps
- Worker authentication uses credential-derived tokens (SHA-256)
- Workers can be banned or suspended via the admin API without restarting the coordinator
- See `docs/security.md` and `config/docker-security.yml` for hardening options

---

## License

See `LICENSE` at the repo root.

---

## Authors

Built by **Joshua Jacob Thomas**, **Sidharth Madhavan**, **Ujjwal Nagar**, and **HR Soorya Dev**  
NIT Calicut · 2026

---

> *Grid-X v1.0.0 — February 2026*
