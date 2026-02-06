import asyncio
import json
import time
import uuid
import sqlite3
from typing import Any, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

DB_PATH = "gridx.db"

# -------------------- DB --------------------

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

DB = db_connect()

def db_init():
    # Minimal tables (based on the doc schema; trimmed fields for MVP). :contentReference[oaicite:4]{index=4}
    DB.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        code TEXT,
        language TEXT,
        status TEXT,
        worker_id TEXT,
        created_at REAL,
        completed_at REAL,
        stdout TEXT,
        stderr TEXT
    );
    """)
    DB.execute("""
    CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        ip TEXT,
        cpu_cores INT,
        gpu_count INT,
        status TEXT,
        last_heartbeat REAL
    );
    """)
    DB.commit()

db_init()

# -------------------- IN-MEMORY RUNTIME STATE --------------------
# Keep active sockets in-memory; persist worker/job metadata in SQLite.

workers_ws: Dict[str, Dict[str, Any]] = {}  # worker_id -> {ws, caps, status, last_seen}
job_queue: asyncio.Queue[str] = asyncio.Queue()
lock = asyncio.Lock()

# -------------------- HELPERS --------------------

def now() -> float:
    return time.time()

def db_upsert_worker(worker_id: str, ip: str, caps: Dict[str, Any], status: str):
    cpu_cores = int(caps.get("cpu_cores") or 0)
    gpu_count = int(1 if caps.get("gpu") else 0)
    DB.execute("""
    INSERT INTO workers(id, ip, cpu_cores, gpu_count, status, last_heartbeat)
    VALUES(?,?,?,?,?,?)
    ON CONFLICT(id) DO UPDATE SET
        ip=excluded.ip,
        cpu_cores=excluded.cpu_cores,
        gpu_count=excluded.gpu_count,
        status=excluded.status,
        last_heartbeat=excluded.last_heartbeat
    """, (worker_id, ip, cpu_cores, gpu_count, status, now()))
    DB.commit()

def db_set_worker_status(worker_id: str, status: str):
    DB.execute("UPDATE workers SET status=?, last_heartbeat=? WHERE id=?",
               (status, now(), worker_id))
    DB.commit()

def db_create_job(job_id: str, user_id: str, code: str, language: str, limits: Dict[str, Any]):
    # store limits in code? for MVP we keep limits in memory message only; DB stores core fields
    DB.execute("""
    INSERT INTO jobs(id, user_id, code, language, status, worker_id, created_at, completed_at, stdout, stderr)
    VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (job_id, user_id, code, language, "queued", None, now(), None, "", ""))
    DB.commit()

def db_set_job_assigned(job_id: str, worker_id: str):
    DB.execute("UPDATE jobs SET status=?, worker_id=? WHERE id=?",
               ("assigned", worker_id, job_id))
    DB.commit()

def db_set_job_running(job_id: str):
    DB.execute("UPDATE jobs SET status=? WHERE id=?", ("running", job_id))
    DB.commit()

def db_set_job_completed(job_id: str, stdout: str, stderr: str, exit_code: int):
    status = "completed" if exit_code == 0 else "failed"
    DB.execute("""
    UPDATE jobs SET status=?, completed_at=?, stdout=?, stderr=? WHERE id=?
    """, (status, now(), stdout, stderr, job_id))
    DB.commit()

def db_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    row = DB.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None

def db_list_workers() -> list[Dict[str, Any]]:
    rows = DB.execute("SELECT * FROM workers").fetchall()
    return [dict(r) for r in rows]

# -------------------- SCHEDULER --------------------

async def dispatch():
    """
    FIFO + first-idle worker. Uses WS sockets in memory and metadata in DB.
    """
    async with lock:
        while not job_queue.empty():
            # find first idle connected worker
            idle_id: Optional[str] = None
            for wid, w in workers_ws.items():
                if w["status"] == "idle":
                    idle_id = wid
                    break
            if idle_id is None:
                return

            job_id = await job_queue.get()
            job_row = db_get_job(job_id)
            if not job_row:
                continue

            # mark assigned
            workers_ws[idle_id]["status"] = "busy"
            db_set_worker_status(idle_id, "busy")
            db_set_job_assigned(job_id, idle_id)

            # Send job to worker. We only support python in MVP.
            # Worker receives {job_id, kind, payload:{script}, limits}
            job_msg = {
                "type": "assign_job",
                "job": {
                    "job_id": job_id,
                    "kind": "python",
                    "payload": {"script": job_row["code"]},
                    "limits": {"cpus": 1, "memory": "256m", "timeout_s": 30},
                }
            }

            ws: WebSocketServerProtocol = workers_ws[idle_id]["ws"]
            try:
                await ws.send(json.dumps(job_msg))
            except Exception:
                # revert if send fails
                workers_ws[idle_id]["status"] = "idle"
                db_set_worker_status(idle_id, "idle")
                DB.execute("UPDATE jobs SET status=?, worker_id=? WHERE id=?",
                           ("queued", None, job_id))
                DB.commit()
                await job_queue.put(job_id)
                return

# -------------------- WORKER WEBSOCKET --------------------

async def handle_worker(ws: WebSocketServerProtocol):
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

                async with lock:
                    workers_ws[worker_id] = {
                        "ws": ws,
                        "caps": caps,
                        "status": "idle",
                        "last_seen": now(),
                    }

                db_upsert_worker(worker_id, peer_ip, caps, "idle")

                await ws.send(json.dumps({"type": "hello_ack", "worker_id": worker_id}))
                await dispatch()
                continue

            if not worker_id:
                continue

            # update heartbeat on any message
            async with lock:
                if worker_id in workers_ws:
                    workers_ws[worker_id]["last_seen"] = now()
            db_set_worker_status(worker_id, workers_ws[worker_id]["status"])

            if t == "hb":
                continue

            if t == "job_started":
                job_id = msg.get("job_id")
                if job_id:
                    db_set_job_running(job_id)
                continue

            if t == "job_log":
                # For MVP, we do not persist logs in DB (keeps it simple).
                # You can add a logs table if needed.
                continue

            if t == "job_result":
                job_id = msg.get("job_id")
                exit_code = int(msg.get("exit_code") or 0)
                stdout = msg.get("stdout", "")
                stderr = msg.get("stderr", "")

                if job_id:
                    db_set_job_completed(job_id, stdout, stderr, exit_code)

                async with lock:
                    if worker_id in workers_ws:
                        workers_ws[worker_id]["status"] = "idle"
                db_set_worker_status(worker_id, "idle")

                await dispatch()
                continue

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if worker_id:
            async with lock:
                workers_ws.pop(worker_id, None)
            # mark worker as offline-ish (still in DB but status idle/unknown)
            DB.execute("UPDATE workers SET status=?, last_heartbeat=? WHERE id=?",
                       ("offline", now(), worker_id))
            DB.commit()

async def ws_router(ws: WebSocketServerProtocol):
    if ws.path != "/ws/worker":
        await ws.close(code=1008, reason="Invalid path")
        return
    await handle_worker(ws)

async def run_ws():
    print("WS workers: ws://0.0.0.0:8080/ws/worker")
    async with websockets.serve(ws_router, "0.0.0.0", 8080, max_size=10 * 1024 * 1024):
        await asyncio.Future()

# -------------------- HTTP API (CLIENTS) --------------------

app = FastAPI(title="Grid-X Coordinator (SQLite + WS MVP)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/jobs")
async def submit_job(body: Dict[str, Any]):
    """
    Submit python code to run. Coordinator stores it and assigns to an idle worker.
    body:
      {
        "user_id": "alice",
        "code": "print('hi')",
        "language": "python"
      }
    """
    code = body.get("code")
    if not code or not isinstance(code, str):
        raise HTTPException(400, "Missing 'code' string")
    language = body.get("language", "python")
    if language != "python":
        raise HTTPException(400, "MVP only supports python")
    user_id = body.get("user_id", "demo")

    job_id = str(uuid.uuid4())
    db_create_job(job_id, user_id, code, language, limits={})

    async with lock:
        await job_queue.put(job_id)

    await dispatch()
    return {"job_id": job_id}

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.get("/workers")
async def list_workers():
    return db_list_workers()

@app.post("/workers/{worker_id}/heartbeat")
async def heartbeat(worker_id: str):
    # Optional heartbeat endpoint mentioned in the doc plan. :contentReference[oaicite:5]{index=5}
    DB.execute("UPDATE workers SET last_heartbeat=? WHERE id=?", (now(), worker_id))
    DB.commit()
    return {"ok": True, "worker_id": worker_id, "ts": now()}

# -------------------- MAIN --------------------

async def main():
    ws_task = asyncio.create_task(run_ws())

    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="info")
    server = uvicorn.Server(config)
    http_task = asyncio.create_task(server.serve())

    await asyncio.gather(ws_task, http_task)

if __name__ == "__main__":
    asyncio.run(main())
