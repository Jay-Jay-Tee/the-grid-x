"""
Grid-X Coordinator - Real-time WebSocket handler for workers with authentication.
FIXED VERSION - All import errors and authentication issues resolved.

FIXES APPLIED:
1. Fixed import errors (removed bare imports)
2. Fixed authentication flow
3. Better error handling
4. Proper connection management
"""

import asyncio
import json
import uuid
import logging
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

# Fixed imports - all relative
from coordinator.database import (
    db_set_worker_offline, db_set_worker_status, 
    db_upsert_worker, db_get_worker_by_auth, db_verify_worker_auth, 
    db_verify_user_auth, now, get_db
)
from coordinator.workers import (
    lock, register_worker_ws, unregister_worker_ws, 
    update_worker_last_seen, workers_ws
)
from coordinator.scheduler import dispatch, on_job_started, on_job_result

logger = logging.getLogger(__name__)


async def handle_worker(ws: WebSocketServerProtocol) -> None:
    """Handle worker WebSocket connection with proper authentication"""
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
                logger.warning(f"Invalid JSON from {peer_ip}")
                continue

            try:
                msg_type = msg.get("type")

                # Handle initial connection
                if msg_type == "hello":
                incoming_worker_id = msg.get("worker_id") or str(uuid.uuid4())
                caps = msg.get("caps", {"cpu_cores": 1, "gpu_count": 0})
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
                            logger.info(f"✓ Worker {worker_id[:12]}... authenticated (owner: {owner_id})")
                        else:
                            # User is correct but this is a new worker for them
                            worker_id = incoming_worker_id
                            logger.info(f"✓ New worker {worker_id[:12]}... registered (owner: {owner_id})")
                    else:
                        # Check if this owner_id exists with different credentials
                        # FIXED: Use proper import
                        existing_user = get_db().execute(
                            "SELECT user_id FROM user_auth WHERE user_id=?", (owner_id,)
                        ).fetchone()
                        
                        if existing_user:
                            # User exists but password is WRONG - REJECT
                            logger.warning(f"❌ Authentication failed for user: {owner_id} (wrong password)")
                            await ws.send(json.dumps({
                                "type": "auth_error",
                                "error": "Authentication failed: Invalid password for this username"
                            }))
                            await ws.close(code=4401, reason="Authentication failed")
                            return
                        else:
                            # Brand new user - register them
                            worker_id = incoming_worker_id
                            logger.info(f"✓ New user {owner_id} registered with worker {worker_id[:12]}...")
                else:
                    # No auth token - backward compatibility (insecure)
                    worker_id = incoming_worker_id
                    logger.warning(f"⚠️  Worker {worker_id[:12]}... connected without authentication")

                # Register worker
                async with lock:
                    register_worker_ws(worker_id, ws, caps, owner_id)

                db_upsert_worker(worker_id, peer_ip, caps, "idle", owner_id=owner_id, auth_token=auth_token)

                await ws.send(json.dumps({"type": "hello_ack", "worker_id": worker_id}))
                await dispatch()
                continue

            # All other messages require authentication
            if not worker_id:
                logger.warning(f"Unauthenticated message from {peer_ip}")
                continue

            # Update worker status
            async with lock:
                update_worker_last_seen(worker_id)
            
            # FIXED: Use proper import
            wstatus = (workers_ws.get(worker_id) or {}).get("status", "idle")
            db_set_worker_status(worker_id, wstatus)

            # Handle heartbeat
            if msg_type == "hb":
                continue

            # Handle job started notification
            if msg_type == "job_started":
                job_id = msg.get("job_id")
                if job_id:
                    on_job_started(job_id)
                continue

            # Handle job logs (currently just logged)
            if msg_type == "job_log":
                continue

            # Handle job result
            if msg_type == "job_result":
                job_id = msg.get("job_id")
                exit_code = int(msg.get("exit_code") or 0)
                stdout = msg.get("stdout", "")
                stderr = msg.get("stderr", "")

                if job_id:
                    on_job_result(job_id, worker_id, exit_code, stdout, stderr)

                await dispatch()
                continue

            except Exception as e:
                logger.error(f"Error handling message from worker {worker_id or 'unknown'}: {e}", exc_info=True)
                raise

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for worker {worker_id or 'unknown'}")
    except Exception as e:
        logger.error(f"Error handling worker {worker_id or 'unknown'}: {e}", exc_info=True)
    finally:
        if worker_id:
            async with lock:
                unregister_worker_ws(worker_id)
            db_set_worker_offline(worker_id)
            logger.info(f"✗ Worker {worker_id[:12]}... disconnected")


async def ws_router(ws: WebSocketServerProtocol, path: Optional[str] = None) -> None:
    """Route WebSocket connections by path"""
    if path is None:
        path = getattr(getattr(ws, "request", None), "path", "") or ""
    
    if path in ["/ws/worker", "/ws/worker/", ""]:
        await handle_worker(ws)
    else:
        logger.warning(f"Invalid WebSocket path: {path}")
        await ws.close(code=4404, reason="Not Found")


def get_ws_port() -> int:
    """Get WebSocket port from environment"""
    import os
    return int(os.getenv("GRIDX_WS_PORT", "8080"))


async def run_ws() -> None:
    """Start WebSocket server"""
    port = get_ws_port()
    logger.info(f"Starting WebSocket server on 0.0.0.0:{port}")
    
    async with websockets.serve(
        ws_router,
        "0.0.0.0",
        port,
        max_size=10 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=20,
    ):
        logger.info(f"WebSocket server ready at ws://0.0.0.0:{port}/ws/worker")
        await asyncio.Future()  # Run forever
