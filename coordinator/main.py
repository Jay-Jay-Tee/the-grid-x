"""
Grid-X Coordinator - Central server (single instance).
Run: python -m coordinator.main  or  uvicorn coordinator.main:app
HTTP API + WebSocket for workers. Credits: tokens decrease on use, increase when your compute is used.
"""

import asyncio
import os
import uuid
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import db_get_job, db_list_workers, get_db, now, db_create_job, db_upsert_worker
from credit_manager import ensure_user, get_balance, deduct, get_job_cost
from scheduler import job_queue, dispatch

# Import so WS server runs
from websocket import run_ws

app = FastAPI(
    title="Grid-X Coordinator",
    description="Central server: jobs, workers, credits. Deploy one instance; workers connect via COORDINATOR_WS.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/jobs")
async def submit_job(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit code to run. Requires sufficient credits (tokens).
    body: { "user_id": "alice", "code": "print('hi')", "language": "python" }
    """
    code = body.get("code")
    if not code or not isinstance(code, str):
        raise HTTPException(400, "Missing 'code' string")
    language = body.get("language", "python")
    if language != "python":
        raise HTTPException(400, "Only python is supported in this version")
    user_id = body.get("user_id", "demo")

    cost = get_job_cost()
    ensure_user(user_id)
    if get_balance(user_id) < cost:
        raise HTTPException(402, f"Insufficient credits. Need {cost}, have {get_balance(user_id)}")

    job_id = str(uuid.uuid4())
    db_create_job(job_id, user_id, code, language, limits={})

    if not deduct(user_id, cost):
        raise HTTPException(402, "Insufficient credits")

    await job_queue.put(job_id)
    await dispatch()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/workers")
async def list_workers():
    return db_list_workers()


@app.post("/workers/register")
async def register_worker_http(body: Dict[str, Any]) -> Dict[str, Any]:
    """HTTP worker registration. Body: {"id": "<worker_id>", "caps": {...}, "ip": "...", "owner_id": "optional"}"""
    worker_id = body.get("id")
    if not worker_id:
        raise HTTPException(400, "Missing 'id' in body")
    caps = body.get("caps", {"cpu_cores": 0, "gpu": False})
    ip = body.get("ip", "http-worker")
    owner_id = body.get("owner_id") or ""
    db_upsert_worker(worker_id, ip, caps, "idle", owner_id=owner_id)
    return {"ok": True, "worker_id": worker_id}


@app.post("/workers/{worker_id}/heartbeat")
async def heartbeat_path(worker_id: str) -> Dict[str, Any]:
    get_db().execute("UPDATE workers SET last_heartbeat=? WHERE id=?", (now(), worker_id))
    get_db().commit()
    return {"ok": True, "worker_id": worker_id, "ts": now()}


@app.post("/workers/heartbeat")
async def heartbeat_body(body: Dict[str, Any]) -> Dict[str, Any]:
    worker_id = body.get("id")
    if not worker_id:
        raise HTTPException(400, "Missing 'id' in body")
    get_db().execute("UPDATE workers SET last_heartbeat=? WHERE id=?", (now(), worker_id))
    get_db().commit()
    return {"ok": True, "worker_id": worker_id, "ts": now()}


# ---------- Credits ----------


@app.get("/credits/{user_id}")
async def get_credits(user_id: str) -> Dict[str, Any]:
    ensure_user(user_id)
    return {"user_id": user_id, "balance": get_balance(user_id)}


def main() -> None:
    http_port = int(os.getenv("GRIDX_HTTP_PORT", "8081"))
    ws_port = int(os.getenv("GRIDX_WS_PORT", "8080"))
    print(f"Grid-X Coordinator HTTP: 0.0.0.0:{http_port}")
    print(f"Grid-X Coordinator WS:   0.0.0.0:{ws_port} path /ws/worker")
    print("Set COORDINATOR_WS=ws://<this-host>:{}/ws/worker on worker machines.".format(ws_port))

    async def run_both() -> None:
        ws_task = asyncio.create_task(run_ws())  # should bind to ws_port inside run_ws()
        config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info")
        server = uvicorn.Server(config)
        http_task = asyncio.create_task(server.serve())
        await asyncio.gather(ws_task, http_task)


    asyncio.run(run_both())


if __name__ == "__main__":
    main()
