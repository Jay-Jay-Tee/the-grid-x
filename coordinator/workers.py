"""
Grid-X Coordinator - Worker registry management (in-memory WS state + DB).
"""

import asyncio
from typing import Any, Dict, Optional

from .database import now

# In-memory: worker_id -> {ws, caps, status, last_seen}
workers_ws: Dict[str, Dict[str, Any]] = {}
lock = asyncio.Lock()


def get_idle_worker_id() -> Optional[str]:
    """Return first idle connected worker id."""
    for wid, w in workers_ws.items():
        # Only consider workers that report they can execute tasks
        caps = w.get("caps") or {}
        can_execute = caps.get("can_execute", True)
        if w.get("status") == "idle" and can_execute:
            return wid
    return None


def set_worker_busy(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["status"] = "busy"
        workers_ws[worker_id]["last_seen"] = now()


def set_worker_idle(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["status"] = "idle"
        workers_ws[worker_id]["last_seen"] = now()


def register_worker_ws(worker_id: str, ws: Any, caps: Dict[str, Any]) -> None:
    workers_ws[worker_id] = {
        "ws": ws,
        "caps": caps,
        "status": "idle",
        "last_seen": now(),
    }


def unregister_worker_ws(worker_id: str) -> None:
    workers_ws.pop(worker_id, None)


def update_worker_last_seen(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["last_seen"] = now()


def get_worker_ws(worker_id: str) -> Optional[Any]:
    entry = workers_ws.get(worker_id)
    return entry["ws"] if entry else None
