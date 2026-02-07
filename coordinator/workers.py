"""
Grid-X Coordinator - Worker registry management (in-memory WS state + DB).

Selection policy change: prefer assigning jobs to other workers first,
then to a coordinator-owned device (if present and capable), and finally
to the submitting user's own worker(s). This helps avoid self-assignment
while still allowing the coordinator device to act as a fallback.
"""

import asyncio
import os
from typing import Any, Dict, Optional

from .database import now, db_set_worker_offline

# In-memory: worker_id -> {ws, caps, status, last_seen}
workers_ws: Dict[str, Dict[str, Any]] = {}
lock = asyncio.Lock()

# Coordinator owner id (optional): set via env for local testing if you
# want a special worker to represent the coordinator device.
COORDINATOR_OWNER = os.getenv("GRIDX_COORDINATOR_OWNER", "coordinator")


def get_idle_worker_id(exclude_owner: Optional[str] = None) -> Optional[str]:
    """Return an idle worker id using priority:

    1) Other workers (owner != submitter and owner != coordinator)
    2) Coordinator-owned worker (owner == COORDINATOR_OWNER)
    3) Submitter's own worker (owner == exclude_owner)

    This preserves the previous `exclude_owner` API but selects the best
    candidate rather than skipping the submitter's workers unconditionally.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"get_idle_worker_id: checking {len(workers_ws)} workers in registry")

    other_workers = []
    coordinator_workers = []
    owner_workers = []

    for wid, w in workers_ws.items():
        caps = w.get("caps") or {}
        # caps may be a dict; if it's a JSON string, ignore and assume capable
        if isinstance(caps, str):
            try:
                import json
                caps = json.loads(caps)
            except Exception:
                caps = {}

        can_execute = caps.get("can_execute", True)
        status = w.get("status")
        owner = w.get("owner_id") or ""

        logger.debug(f"  Worker {wid[:12]}...: status={status}, can_execute={can_execute}, owner={owner}, caps={caps}")

        if status != "idle" or not can_execute:
            continue

        # Categorize
        if owner and owner == exclude_owner:
            owner_workers.append(wid)
        elif owner and owner == COORDINATOR_OWNER:
            coordinator_workers.append(wid)
        else:
            other_workers.append(wid)

    # Prefer other workers, then coordinator device, then submitter's own
    if other_workers:
        logger.debug(f"  → Selected other worker {other_workers[0][:12]}...")
        return other_workers[0]
    if coordinator_workers:
        logger.debug(f"  → Selected coordinator worker {coordinator_workers[0][:12]}...")
        return coordinator_workers[0]
    if owner_workers:
        logger.debug(f"  → Selected owner worker {owner_workers[0][:12]}...")
        return owner_workers[0]

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


async def disconnect_worker(worker_id: str) -> bool:
    """Force-disconnect a worker websocket and mark it offline."""
    try:
        async with lock:
            entry = workers_ws.get(worker_id)
            ws = entry.get("ws") if entry else None

            if not entry:
                return False

            # Attempt graceful close
            if ws:
                try:
                    await ws.close(code=4400, reason="Disconnected by admin")
                except Exception:
                    pass

            unregister_worker_ws(worker_id)

        try:
            db_set_worker_offline(worker_id)
        except Exception:
            pass

        return True
    except Exception:
        return False
