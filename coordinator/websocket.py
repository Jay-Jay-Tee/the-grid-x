"""
Grid-X Coordinator - Real-time WebSocket handler for workers.
"""

import asyncio
import json
import uuid
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from database import db_init, db_set_worker_offline, db_set_worker_status, db_upsert_worker, now
from workers import lock, register_worker_ws, unregister_worker_ws, update_worker_last_seen
from scheduler import dispatch, job_queue, on_job_started, on_job_result


async def handle_worker(ws: WebSocketServerProtocol) -> None:
    worker_id: Optional[str] = None
    peer_ip = "unknown"
    try:
        peer = ws.remote_address
        if peer and len(peer) >= 1:
            peer_ip = str(peer[0])
    except Exception:
        pass

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            t = msg.get("type")

            if t == "hello":
                worker_id = msg.get("worker_id") or str(uuid.uuid4())
                caps = msg.get("caps", {"cpu_cores": 0, "gpu": False})
                owner_id = msg.get("owner_id") or ""  # Optional: user who gets credits when jobs run here

                async with lock:
                    register_worker_ws(worker_id, ws, caps)

                db_upsert_worker(worker_id, peer_ip, caps, "idle", owner_id=owner_id)

                await ws.send(json.dumps({"type": "hello_ack", "worker_id": worker_id}))
                await dispatch()
                continue

            if not worker_id:
                continue

            async with lock:
                update_worker_last_seen(worker_id)
            # Keep DB in sync with in-memory status
            from workers import workers_ws
            wstatus = (workers_ws.get(worker_id) or {}).get("status", "idle")
            db_set_worker_status(worker_id, wstatus)

            if t == "hb":
                continue

            if t == "job_started":
                job_id = msg.get("job_id")
                if job_id:
                    on_job_started(job_id)
                continue

            if t == "job_log":
                continue

            if t == "job_result":
                job_id = msg.get("job_id")
                exit_code = int(msg.get("exit_code") or 0)
                stdout = msg.get("stdout", "")
                stderr = msg.get("stderr", "")

                if job_id:
                    on_job_result(job_id, worker_id, exit_code, stdout, stderr)

                await dispatch()
                continue

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if worker_id:
            async with lock:
                unregister_worker_ws(worker_id)
            db_set_worker_offline(worker_id)


async def ws_router(ws: WebSocketServerProtocol, path: Optional[str] = None) -> None:
    """Route by path: /ws/worker for worker connections."""
    if path is None:
        path = getattr(getattr(ws, "request", None), "path", "") or ""
    if path == "/ws/worker" or path == "/ws/worker/" or path == "":
        await handle_worker(ws)
    else:
        await ws.close(code=4404, reason="Not Found")


def get_ws_port() -> int:
    import os
    return int(os.getenv("GRIDX_WS_PORT", "8080"))


async def run_ws() -> None:
    port = get_ws_port()
    print(f"Grid-X Coordinator WS: 0.0.0.0:{port} path /ws/worker")
    async with websockets.serve(
        ws_router,
        "0.0.0.0",
        port,
        max_size=10 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()
