"""
Grid-X Coordinator - Worker registry management (in-memory WS state + DB).
"""

import asyncio
from typing import Any, Dict, Optional

from .database import now

# In-memory: worker_id -> {ws, caps, status, last_seen}
workers_ws: Dict[str, Dict[str, Any]] = {}
lock = asyncio.Lock()


def get_idle_worker_id(exclude_owner: Optional[str] = None) -> Optional[str]:
    """Return first idle connected worker id.

    If `exclude_owner` is provided, skip workers whose `owner_id` matches it.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"get_idle_worker_id: checking {len(workers_ws)} workers in registry")
    for wid, w in workers_ws.items():
        # Only consider workers that report they can execute tasks
        caps = w.get("caps") or {}
        can_execute = caps.get("can_execute", True)
        status = w.get("status")
        owner = w.get("owner_id")
        logger.debug(f"  Worker {wid[:12]}...: status={status}, can_execute={can_execute}, owner={owner}, caps={caps}")
        if exclude_owner and owner and owner == exclude_owner:
            logger.debug(f"  → Skipping worker {wid[:12]}... (owner excluded)")
            continue
        if status == "idle" and can_execute:
            logger.debug(f"  → Selected worker {wid[:12]}...")
            return wid
    logger.debug(f"  → No idle worker found")
    return None


def set_worker_busy(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["status"] = "busy"
        workers_ws[worker_id]["last_seen"] = now()


def set_worker_idle(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["status"] = "idle"
        workers_ws[worker_id]["last_seen"] = now()


def register_worker_ws(worker_id: str, ws: Any, caps: Dict[str, Any], owner_id: str = "") -> None:
    workers_ws[worker_id] = {
        "ws": ws,
        "caps": caps,
        "status": "idle",
        "last_seen": now(),
        "owner_id": owner_id,
    }


def unregister_worker_ws(worker_id: str) -> None:
    workers_ws.pop(worker_id, None)


def update_worker_last_seen(worker_id: str) -> None:
    if worker_id in workers_ws:
        workers_ws[worker_id]["last_seen"] = now()


def get_worker_ws(worker_id: str) -> Optional[Any]:
    entry = workers_ws.get(worker_id)
    return entry["ws"] if entry else None
