# FILEDIR — repository map

A compact map of the repository layout and the main responsibilities of each top-level folder.

```text
GRID-X/
├── coordinator/          # Central API + scheduler (FastAPI)
│   ├── __init__.py
│   ├── main.py           # HTTP + WebSocket server entrypoint
│   ├── database.py       # Database helpers (SQLite by default)
│   ├── scheduler.py      # Job assignment logic
│   ├── workers.py        # Worker registry management
│   ├── credit_manager.py # Credit/balance system
│   ├── websocket.py      # WebSocket handlers
│   └── Dockerfile
├── worker/               # Worker agent components (multiple instances)
│   ├── __init__.py
│   ├── main.py           # Worker entrypoint (CLI/agent)
│   ├── docker_manager.py # Docker container lifecycle helpers
│   ├── task_executor.py  # Task execution orchestration
│   ├── task_queue.py     # Queue abstraction (in-memory / adapters)
│   ├── resource_monitor.py # Host resource sampling (psutil)
│   └── Dockerfile
├── worker_app/           # Optional GUI worker (Tkinter/CTk) and helpers
│   ├── main.py
│   └── ui/               # UI frames and components
├── sdk/                  # TypeScript client SDK for external users
├── common/               # Shared code: schemas, utils, constants
├── config/               # env examples and deployment snippets
├── scripts/              # Convenience scripts (setup, tests)
├── docs/                 # Design notes, API reference, deployment guides
├── tests/                # Unit and integration tests
├── docker-compose.yml
├── Procfile
├── requirements.txt      # Top-level dependencies for local development
├── README.md             # Project overview & quickstart
└── FILEDIR.md            # This file (directory map)
```

See `README.md` for a short quickstart and configuration notes.