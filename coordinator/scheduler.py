"""
Grid-X Coordinator - Job assignment logic (FIFO + first idle worker).
"""

import asyncio
import json
from typing import Any, Dict, Optional

from .database import (
    get_db,
    db_get_job,
    db_set_job_assigned,
    db_set_job_completed,
    db_set_job_running,
    db_set_worker_status,
    db_get_worker,
)
from .workers import (
    get_idle_worker_id,
    get_worker_ws,
    lock,
    set_worker_busy,
    set_worker_idle,
    unregister_worker_ws,
)
from .credit_manager import credit, get_worker_reward
import logging

logger = logging.getLogger(__name__)

# Job queue: job_id strings
job_queue: asyncio.Queue[str] = asyncio.Queue()


async def watchdog_loop(check_interval: int = 15, heartbeat_timeout: int = 30) -> None:
    """Periodically requeue jobs stuck in 'running' whose worker heartbeat is stale.

    - check_interval: seconds between checks
    - heartbeat_timeout: seconds since last_heartbeat after which worker is considered dead
    """
    while True:
        try:
            conn = get_db()
            rows = conn.execute(
                "SELECT id, worker_id FROM jobs WHERE status='running'"
            ).fetchall()

            for r in rows:
                job_id = r["id"]
                worker_id = r["worker_id"]
                if not worker_id:
                    continue

                # If worker has an active in-memory websocket, skip (it's connected)
                try:
                    ws = get_worker_ws(worker_id)
                    if ws:
                        continue
                except Exception:
                    pass

                w = conn.execute("SELECT last_heartbeat FROM workers WHERE id=?", (worker_id,)).fetchone()
                last = w["last_heartbeat"] if w else None

                # If no heartbeat recorded or it's older than timeout, requeue
                import time
                now_ts = time.time()
                if not last or (now_ts - float(last) > heartbeat_timeout):
                    # Mark worker offline and requeue
                    try:
                        conn.execute("UPDATE workers SET status=? WHERE id=?", ("offline", worker_id))
                        conn.execute(
                            "UPDATE jobs SET status=?, worker_id=? WHERE id=?",
                            ("queued", None, job_id),
                        )
                        conn.commit()
                        # Put back into in-memory queue for dispatch
                        try:
                            await job_queue.put(job_id)
                        except Exception:
                            pass
                        logger.info(f"Watchdog requeued job {job_id} from worker {worker_id}")
                    except Exception:
                        conn.rollback()

        except Exception:
            pass

        await asyncio.sleep(check_interval)


async def dispatch() -> None:
    """
    FIFO + first idle worker. Assigns queued jobs to idle workers over WebSocket.
    On job completion, credits worker owner.
    """
    try:
        async with lock:
            while not job_queue.empty():
                try:
                    job_id = job_queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                job_row = db_get_job(job_id)
                if not job_row:
                    logger.warning(f"dispatch: Job {job_id} not found in DB")
                    continue

                # Prefer an idle worker that is NOT owned by the job submitter
                owner_to_exclude = (job_row.get("user_id") or "").strip()
                idle_id: Optional[str] = get_idle_worker_id(exclude_owner=owner_to_exclude)
                if idle_id is None:
                    logger.warning(f"dispatch: No idle worker available (excluding owner={owner_to_exclude}). Queue size: {job_queue.qsize()}")
                    # Put job back to queue head by re-adding and return
                    try:
                        await job_queue.put(job_id)
                    except Exception:
                        pass
                    return

                logger.info(f"dispatch: Assigning job {job_id} to worker {idle_id}")
                set_worker_busy(idle_id)
                db_set_worker_status(idle_id, "busy")
                db_set_job_assigned(job_id, idle_id)

                job_msg = {
                    "type": "assign_job",
                    "job": {
                        "job_id": job_id,
                        "kind": job_row["language"] or "python",
                        "payload": {"script": job_row["code"]},
                        "limits": {
                            "cpus": 1,
                            "memory": "256m",
                            "timeout_s": 30,
                        },
                    },
                }

                ws = get_worker_ws(idle_id)
                if not ws:
                    # Revert and re-queue
                    set_worker_idle(idle_id)
                    db_set_worker_status(idle_id, "idle")
                    get_db().execute(
                        "UPDATE jobs SET status=?, worker_id=? WHERE id=?",
                        ("queued", None, job_id),
                    )
                    get_db().commit()
                    await job_queue.put(job_id)
                    return

                try:
                    await ws.send(json.dumps(job_msg))
                except Exception:
                    set_worker_idle(idle_id)
                    db_set_worker_status(idle_id, "idle")
                    get_db().execute(
                        "UPDATE jobs SET status=?, worker_id=? WHERE id=?",
                        ("queued", None, job_id),
                    )
                    get_db().commit()
                    await job_queue.put(job_id)
                    return
    except Exception:
        pass


def on_job_started(job_id: str) -> None:
    db_set_job_running(job_id)


def on_job_result(
    job_id: str,
    worker_id: str,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> None:
    logger.info(f"on_job_result: Job {job_id} completed on worker {worker_id} (exit_code={exit_code})")
    db_set_job_completed(job_id, stdout, stderr, exit_code)
    set_worker_idle(worker_id)
    db_set_worker_status(worker_id, "idle")

    # Credit worker owner when their compute is used
    worker_row = db_get_worker(worker_id)
    if worker_row and worker_row.get("owner_id"):
        owner_id = (worker_row.get("owner_id") or "").strip()
        if owner_id:
            reward = get_worker_reward()
            credit(owner_id, reward)
            logger.info(f"on_job_result: Credited {reward} to worker owner {owner_id}")

    # Dispatch next job (caller should await dispatch() after this)
    asyncio.create_task(dispatch())
