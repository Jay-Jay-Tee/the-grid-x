"""
Grid-X Coordinator - Real-time WebSocket handler for workers with authentication.
FIXED VERSION - Properly rejects wrong passwords instead of creating new workers.
"""

import asyncio
import json
import uuid
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from .database import (
    db_init, db_set_worker_offline, db_set_worker_status, 
    db_upsert_worker, db_get_worker_by_auth, db_verify_worker_auth, 
    db_verify_user_auth, now, get_db
)
from .workers import lock, register_worker_ws, unregister_worker_ws, update_worker_last_seen
from .scheduler import dispatch, job_queue, on_job_started, on_job_result


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

            try:
                t = msg.get("type")

                if t == "hello":
                    incoming_worker_id = msg.get("worker_id") or str(uuid.uuid4())
                    caps = msg.get("caps", {"cpu_cores": 0, "gpu": False})
                    owner_id = msg.get("owner_id") or ""
                    auth_token = msg.get("auth_token", "")

                    # FIXED AUTHENTICATION LOGIC
                    if auth_token and owner_id:
                        # Check if user already has credentials registered
                        user_exists = db_verify_user_auth(owner_id, auth_token)
                        
                        if user_exists:
                            # User exists and password is correct
                            # Check if they have an existing worker
                            existing_worker = db_get_worker_by_auth(owner_id, auth_token)
                            
                            if existing_worker:
                                # Reconnecting with existing worker
                                worker_id = existing_worker['id']
                                print(f"✓ Worker {worker_id[:12]}... authenticated (owner: {owner_id})")
                            else:
                                # User is correct but this is a new worker for them
                                worker_id = incoming_worker_id
                                print(f"✓ New worker {worker_id[:12]}... registered (owner: {owner_id})")
                        else:
                            # Check if this owner_id exists in the database with different credentials
                            existing_user = get_db().execute(
                                "SELECT user_id FROM user_auth WHERE user_id=?", (owner_id,)
                            ).fetchone()
                            
                            if existing_user:
                                # User exists but password is WRONG - REJECT
                                print(f"❌ Authentication failed for user: {owner_id} (wrong password)")
                                await ws.send(json.dumps({
                                    "type": "auth_error",
                                    "error": "Authentication failed: Invalid password for this username"
                                }))
                                await ws.close(code=4401, reason="Authentication failed")
                                return
                            else:
                                # Brand new user - register them
                                worker_id = incoming_worker_id
                                print(f"✓ New user {owner_id} registered with worker {worker_id[:12]}...")
                    else:
                        # No auth token - backward compatibility (insecure)
                        worker_id = incoming_worker_id
                        print(f"⚠️  Worker {worker_id[:12]}... connected without authentication")

                    async with lock:
                        register_worker_ws(worker_id, ws, caps, owner_id)

                    db_upsert_worker(worker_id, peer_ip, caps, "idle", owner_id=owner_id, auth_token=auth_token)

                    try:
                        await ws.send(json.dumps({"type": "hello_ack", "worker_id": worker_id}))
                    except websockets.exceptions.ConnectionClosedOK:
                        # Worker closed connection before we could send hello_ack
                        # This is a race condition - worker likely timed out waiting
                        print(f"⚠️  Worker {worker_id[:12]}... closed connection during handshake (timeout?)")
                        return
                    except websockets.exceptions.ConnectionClosed as e:
                        # Connection was closed unexpectedly
                        print(f"⚠️  Worker {worker_id[:12]}... connection closed: {e}")
                        return
                    
                    await dispatch()
                    continue

                if not worker_id:
                    continue

                async with lock:
                    update_worker_last_seen(worker_id)
                # Keep DB in sync with in-memory status
                from .workers import workers_ws
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

            except Exception as e:
                print(f"❌ Error handling message from worker {worker_id or 'unknown'}: {e}")
                import traceback
                traceback.print_exc()
                # Don't re-raise ConnectionClosedOK - just exit loop
                if not isinstance(e, websockets.exceptions.ConnectionClosedOK):
                    raise

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"❌ Unexpected error in worker handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if worker_id:
            async with lock:
                unregister_worker_ws(worker_id)
            db_set_worker_offline(worker_id)

            # Requeue any jobs that were marked running on this worker
            try:
                conn = get_db()
                rows = conn.execute(
                    "SELECT id FROM jobs WHERE status=? AND worker_id=?",
                    ("running", worker_id),
                ).fetchall()

                for r in rows:
                    job_id = r["id"]
                    conn.execute(
                        "UPDATE jobs SET status=?, worker_id=? WHERE id=?",
                        ("queued", None, job_id),
                    )
                    conn.commit()
                    # Put back on in-memory queue for dispatch
                    try:
                        await job_queue.put(job_id)
                    except Exception:
                        pass

                if rows:
                    print(f"⚠️  Requeued {len(rows)} job(s) from disconnected worker {worker_id[:12]}...")
            except Exception as e:
                print(f"⚠️  Error requeuing jobs from {worker_id[:12]}: {e}")

            print(f"✗ Worker {worker_id[:12]}... disconnected")


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
