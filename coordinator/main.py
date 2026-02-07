"""
Grid-X Coordinator - Central server (single instance).

FIXED VERSION - Addresses critical issues:
1. Double credit deduction bug
2. Input validation
3. Proper error handling
4. Transaction support

Run: python -m coordinator.main  or  uvicorn coordinator.main:app
HTTP API + WebSocket for workers. Credits: tokens decrease on use, increase when your compute is used.
"""

import asyncio
import os
import uuid
import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Import from common module (now properly implemented)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils import (
    validate_uuid,
    validate_user_id,
    sanitize_string,
    now,
    generate_job_id
)
from common.constants import (
    STATUS_QUEUED,
    DEFAULT_LANGUAGE,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_PAYMENT_REQUIRED,
    HTTP_INTERNAL_ERROR
)

from coordinator.database import (
    db_get_job,
    db_get_worker,
    db_list_jobs_by_user,
    db_list_workers,
    db_list_recent_jobs,
    db_list_recently_completed_jobs,
    db_list_jobs_with_workers,
    db_list_users,
    get_db,
    db_create_job,
    db_upsert_worker,
    db_set_worker_restriction,
    init_db
)
from coordinator.credit_manager import (
    ensure_user,
    get_balance,
    deduct,
    credit,
    get_max_reserve,
)
from coordinator.scheduler import job_queue, dispatch, watchdog_loop
from coordinator.workers import workers_ws, disconnect_worker, broadcast_to_all_workers

# Import so WS server runs
from coordinator.websocket import run_ws

ADMIN_STATIC_DIR = os.path.join(os.path.dirname(__file__), "admin_ui")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Grid-X Coordinator...")
    init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Grid-X Coordinator...")
    # Close database connections
    db = get_db()
    if db:
        db.close()
    logger.info("✅ Shutdown complete")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Grid-X Coordinator",
    description="Central server: jobs, workers, credits. Deploy one instance; workers connect via COORDINATOR_WS.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve admin static assets if present
if os.path.isdir(ADMIN_STATIC_DIR):
    app.mount(
        "/admin/static",
        StaticFiles(directory=ADMIN_STATIC_DIR),
        name="admin_static",
    )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.status_code,
            "timestamp": now()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=HTTP_INTERNAL_ERROR,
        content={
            "error": "Internal server error",
            "code": HTTP_INTERNAL_ERROR,
            "timestamp": now()
        }
    )


# ============================================================================
# JOB ENDPOINTS
# ============================================================================

@app.post("/jobs")
async def submit_job(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit code to run. Requires sufficient credits (tokens).
    
    FIXED: No more double credit check! Credits are deducted BEFORE job creation.
    This prevents race conditions and free jobs.
    
    Request body:
    {
        "user_id": "alice",
        "code": "print('hello world')",
        "language": "python"
    }
    
    Returns:
    {
        "job_id": "uuid-string"
    }
    """
    # ========== INPUT VALIDATION ==========
    code = body.get("code")
    if not code or not isinstance(code, str):
        raise HTTPException(HTTP_BAD_REQUEST, "Missing or invalid 'code' field")
    
    if len(code) > 1_000_000:  # 1MB limit
        raise HTTPException(HTTP_BAD_REQUEST, "Code exceeds maximum size of 1MB")
    
    language = body.get("language", DEFAULT_LANGUAGE)
    if language not in ["python", "javascript", "node", "bash"]:
        raise HTTPException(HTTP_BAD_REQUEST, f"Unsupported language: {language}")

    user_id = body.get("user_id", "demo")
    if not validate_user_id(user_id):
        raise HTTPException(HTTP_BAD_REQUEST, f"Invalid user_id: {user_id}")
    
    # Sanitize inputs
    code = sanitize_string(code, max_length=1_000_000)
    user_id = sanitize_string(user_id, max_length=64)

    # Time-based credits: reserve max cost from job timeout (refund unused when job completes)
    limits = body.get("limits") or {}
    timeout_seconds = limits.get("timeout_s") or 60
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 60
    reserved = get_max_reserve(timeout_seconds)
    
    # ========== CREDIT HANDLING ==========
    ensure_user(user_id)
    current_balance = get_balance(user_id)
    if current_balance < reserved:
        raise HTTPException(
            HTTP_PAYMENT_REQUIRED,
            f"Insufficient credits. Reserve required: {reserved} (based on timeout), have {current_balance}"
        )
    
    if not deduct(user_id, reserved):
        raise HTTPException(
            HTTP_PAYMENT_REQUIRED,
            f"Failed to deduct credits. Balance: {get_balance(user_id)}"
        )
    
    # ========== JOB CREATION ==========
    job_id = generate_job_id()
    
    try:
        db_create_job(
            job_id=job_id,
            user_id=user_id,
            code=code,
            language=language,
            limits={"timeout_s": timeout_seconds},
            reserved_cost=reserved,
        )
        
        await job_queue.put(job_id)
        await dispatch()
        
        logger.info(f"Job {job_id} submitted by user {user_id}, reserved={reserved} (time-based)")
        
        return {
            "job_id": job_id,
            "status": STATUS_QUEUED,
            "reserved": reserved,
            "message": "Charged by compute time when job completes; unused reserve refunded.",
        }
        
    except Exception as e:
        logger.error(f"Job creation failed: {e}, refunding {reserved} credits to {user_id}")
        credit(user_id, reserved)
        raise HTTPException(
            HTTP_INTERNAL_ERROR,
            f"Job creation failed: {str(e)}"
        )


@app.get("/jobs")
async def list_jobs(user_id: Optional[str] = None, limit: int = 50) -> Any:
    """
    List jobs for a user. Requires user_id query parameter.
    Returns list of jobs, most recent first.
    """
    if not user_id:
        raise HTTPException(HTTP_BAD_REQUEST, "user_id query parameter is required")
    if not validate_user_id(user_id):
        raise HTTPException(HTTP_BAD_REQUEST, f"Invalid user_id: {user_id}")
    limit = min(max(1, limit), 100)
    jobs = db_list_jobs_by_user(user_id, limit=limit)
    return jobs


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """
    Get job details by ID.
    
    FIXED: Added input validation for job_id
    """
    # Validate UUID format
    if not validate_uuid(job_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid job ID format")
    
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(HTTP_NOT_FOUND, "Job not found")
    
    return job


# ============================================================================
# WORKER ENDPOINTS
# ============================================================================

@app.get("/workers")
async def list_workers():
    """List all registered workers"""
    workers = db_list_workers()
    # Return just the list for backward compatibility
    workers_list = []
    for w in workers:
        worker_dict = dict(w) if hasattr(w, 'keys') else w
        workers_list.append(worker_dict)
    return workers_list


@app.post("/workers/register")
async def register_worker_http(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    HTTP worker registration.
    
    Request body:
    {
        "id": "<worker_id>",
        "caps": {"cpu_cores": 4, "gpu": false},
        "ip": "192.168.1.100",
        "owner_id": "alice"
    }
    
    FIXED: Added input validation
    """
    worker_id = body.get("id")
    if not worker_id:
        raise HTTPException(HTTP_BAD_REQUEST, "Missing 'id' in body")
    
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    
    caps = body.get("caps", {"cpu_cores": 1, "gpu_count": 0})
    ip = sanitize_string(body.get("ip", "http-worker"), max_length=255)
    owner_id = sanitize_string(body.get("owner_id", ""), max_length=64)
    
    if owner_id and not validate_user_id(owner_id):
        raise HTTPException(HTTP_BAD_REQUEST, f"Invalid owner_id: {owner_id}")
    
    db_upsert_worker(
        worker_id=worker_id,
        ip=ip,
        caps=caps,
        status="idle",
        owner_id=owner_id
    )
    
    logger.info(f"Worker {worker_id} registered via HTTP, owner={owner_id}")
    
    return {
        "success": True,
        "worker_id": worker_id,
        "status": "registered"
    }


@app.post("/workers/{worker_id}/heartbeat")
async def heartbeat_path(worker_id: str) -> Dict[str, Any]:
    """
    Worker heartbeat via path parameter.
    
    FIXED: Added input validation
    """
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    
    timestamp = now()
    get_db().execute(
        "UPDATE workers SET last_heartbeat=? WHERE id=?",
        (timestamp, worker_id)
    )
    get_db().commit()
    
    return {
        "success": True,
        "worker_id": worker_id,
        "timestamp": timestamp
    }


@app.post("/workers/heartbeat")
async def heartbeat_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker heartbeat via request body.
    
    FIXED: Added input validation
    """
    worker_id = body.get("id")
    if not worker_id:
        raise HTTPException(HTTP_BAD_REQUEST, "Missing 'id' in body")
    
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    
    timestamp = now()
    get_db().execute(
        "UPDATE workers SET last_heartbeat=? WHERE id=?",
        (timestamp, worker_id)
    )
    get_db().commit()
    
    return {
        "success": True,
        "worker_id": worker_id,
        "timestamp": timestamp
    }


# ============================================================================
# CREDIT ENDPOINTS
# ============================================================================

@app.get("/credits/{user_id}")
async def get_credits(user_id: str) -> Dict[str, Any]:
    """
    Get user credit balance.
    
    FIXED: Added input validation
    """
    if not validate_user_id(user_id):
        raise HTTPException(HTTP_BAD_REQUEST, f"Invalid user_id: {user_id}")
    
    ensure_user(user_id)
    balance = get_balance(user_id)
    
    return {
        "user_id": user_id,
        "balance": balance,
        "timestamp": now()
    }


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "grid-x-coordinator",
        "timestamp": now()
    }


@app.get("/status")
async def get_status():
    """Get coordinator status"""
    workers = db_list_workers()
    active_workers = [w for w in workers if w.get('status') == 'idle' or w.get('status') == 'busy']
    
    return {
        "service": "Grid-X Coordinator",
        "version": "1.0.0",
        "uptime": "running",
        "workers": {
            "total": len(workers),
            "active": len(active_workers)
        },
        "queue_size": job_queue.qsize(),
        "timestamp": now()
    }


# ============================================================================
# ADMIN ENDPOINTS & UI
# ============================================================================


@app.get("/admin/overview")
async def admin_overview(limit: int = 50) -> Dict[str, Any]:
    """Admin snapshot: workers, jobs, and users."""
    limit = min(max(int(limit), 1), 200)

    workers = db_list_workers()
    worker_ids = {w["id"] for w in workers}
    # Include connected workers that may not yet be in DB
    for wid, entry in workers_ws.items():
        if wid not in worker_ids:
            workers.append({
                "id": wid,
                "owner_id": entry.get("owner_id") or "",
                "status": entry.get("status") or "idle",
                "ip": "connected",
                "last_heartbeat": entry.get("last_seen"),
                "restriction": None,
            })
    running_jobs = db_list_jobs_with_workers(["running"], limit)
    queued_jobs = db_list_jobs_with_workers(["queued"], limit)
    recent_jobs = db_list_recent_jobs(limit)
    recently_completed_jobs = db_list_recently_completed_jobs(limit)
    users = db_list_users(200)

    return {
        "workers": workers,
        "connected_worker_ids": list(workers_ws.keys()),
        "jobs": {
            "running": running_jobs,
            "queued": queued_jobs,
            "recent": recent_jobs,
            "recently_completed": recently_completed_jobs,
        },
        "users": users,
        "timestamp": now(),
    }


@app.post("/admin/workers/{worker_id}/disconnect")
async def admin_disconnect_worker(worker_id: str) -> Dict[str, Any]:
    """Force-disconnect a worker websocket and mark it offline."""
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")

    ok = await disconnect_worker(worker_id)
    if not ok:
        raise HTTPException(HTTP_NOT_FOUND, "Worker not connected or already offline")

    return {"success": True, "worker_id": worker_id}


def _ensure_worker_exists_for_restriction(worker_id: str) -> bool:
    """Ensure worker row exists (create from workers_ws if connected but not in DB). Return True if exists."""
    if db_get_worker(worker_id):
        return True
    # Worker may be connected but not yet in DB - get from workers_ws and insert
    entry = workers_ws.get(worker_id)
    if entry:
        owner_id = entry.get("owner_id") or ""
        caps = entry.get("caps") or {}
        import json
        conn = get_db()
        conn.execute(
            """
            INSERT INTO workers (id, owner_id, ip, caps, status, registered_at, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (worker_id, owner_id, "unknown", json.dumps(caps), "offline", now(), now()),
        )
        conn.commit()
        return True
    return False


@app.post("/admin/workers/{worker_id}/ban")
async def admin_ban_worker(worker_id: str) -> Dict[str, Any]:
    """Ban a worker - disconnect if connected and prevent future connections."""
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    if not _ensure_worker_exists_for_restriction(worker_id):
        raise HTTPException(HTTP_NOT_FOUND, "Worker not found")
    await disconnect_worker(worker_id)
    db_set_worker_restriction(worker_id, "banned")
    return {"success": True, "worker_id": worker_id, "restriction": "banned"}


@app.post("/admin/workers/{worker_id}/suspend")
async def admin_suspend_worker(worker_id: str) -> Dict[str, Any]:
    """Suspend a worker - disconnect if connected and prevent connections until unsuspended."""
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    if not _ensure_worker_exists_for_restriction(worker_id):
        raise HTTPException(HTTP_NOT_FOUND, "Worker not found")
    await disconnect_worker(worker_id)
    db_set_worker_restriction(worker_id, "suspended")
    return {"success": True, "worker_id": worker_id, "restriction": "suspended"}


@app.post("/admin/workers/{worker_id}/unsuspend")
async def admin_unsuspend_worker(worker_id: str) -> Dict[str, Any]:
    """Remove suspend restriction from a worker."""
    if not validate_uuid(worker_id):
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid worker ID format")
    if not _ensure_worker_exists_for_restriction(worker_id):
        raise HTTPException(HTTP_NOT_FOUND, "Worker not found")
    db_set_worker_restriction(worker_id, None)
    return {"success": True, "worker_id": worker_id, "restriction": None}


@app.post("/admin/broadcast")
async def admin_broadcast(request: Request) -> Dict[str, Any]:
    """Broadcast a message to all connected worker nodes."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(HTTP_BAD_REQUEST, "Invalid JSON body")
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(HTTP_BAD_REQUEST, "Message cannot be empty")
    message = sanitize_string(message, max_length=2000)
    count = await broadcast_to_all_workers(message)
    return {"success": True, "workers_notified": count}


@app.get("/admin")
async def admin_page():
    """Serve the admin dashboard page."""
    index_path = os.path.join(ADMIN_STATIC_DIR, "admin.html")
    if not os.path.exists(index_path):
        raise HTTPException(HTTP_NOT_FOUND, "Admin UI not found. Did you run the frontend scaffold?")
    return FileResponse(index_path, media_type="text/html")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """Main entry point"""
    http_port = int(os.getenv("GRIDX_HTTP_PORT", "8081"))
    ws_port = int(os.getenv("GRIDX_WS_PORT", "8080"))
    
    print("=" * 60)
    print("🌐 Grid-X Coordinator - FIXED VERSION 1.0.0")
    print("=" * 60)
    print(f"📡 HTTP API:    http://0.0.0.0:{http_port}")
    print(f"🔌 WebSocket:   ws://0.0.0.0:{ws_port}/ws/worker")
    print("=" * 60)
    print(f"💡 Configure workers with:")
    print(f"   COORDINATOR_WS=ws://<this-host>:{ws_port}/ws/worker")
    print("=" * 60)
    
    async def run_both() -> None:
        """Run both HTTP and WebSocket servers"""
        # Start WebSocket server
        ws_task = asyncio.create_task(run_ws())
        # Start scheduler watchdog to requeue stuck jobs
        watchdog_task = asyncio.create_task(watchdog_loop())
        
        # Start HTTP server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=http_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        http_task = asyncio.create_task(server.serve())
        
        # Wait for both
        await asyncio.gather(ws_task, http_task)
    
    try:
        asyncio.run(run_both())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
