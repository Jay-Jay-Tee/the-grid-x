# coordinator.py
# Simple Grid-X Coordinator (MVP)
# - Workers connect via WebSocket: ws://<ip>:8080/ws/worker
# - Users submit jobs via HTTP:     http://<ip>:8081/jobs  (JSON with python script)
# - Coordinator assigns FIFO jobs to first idle worker
#
# Install:
#   pip install websockets fastapi uvicorn
#
# Run:
#   python coordinator.py
#
# Submit job:
#   curl -X POST http://<ip>:8081/jobs -H "Content-Type: application/json" \
#     -d '{"kind":"python","payload":{"script":"print(123)"},"limits":{"cpus":1,"memory":"256m","timeout_s":30}}'
#
# Check job:
#   curl http://<ip>:8081/jobs/<job_id>
#
# List workers:
#   curl http://<ip>:8081/workers

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# -------------------- IN-MEMORY STATE --------------------

workers: Dict[str, Dict[str, Any]] = {}     # worker_id -> { ws, status, caps, last_seen }
jobs: Dict[str, Dict[str, Any]] = {}        # job_id -> job
job_queue: asyncio.Queue[str] = asyncio.Queue()

lock = asyncio.Lock()


# -------------------- SCHEDULER --------------------

async def dispatch():
    """
    Assign queued jobs to idle workers, FIFO.
    """
    async with lock:
        while not job_queue.empty():
            # find first idle worker
            idle_id: Optional[str] = None
            for wid, w in workers.items():
                if w["status"] == "idle":
                    idle_id = wid
                    break
            if idle_id is None:
                return

            job_id = await job_queue.get()
            job = jobs.get(job_id)
            if not job:
                continue

            worker = workers[idle_id]
            worker["status"] = "busy"

            job["status"] = "assigned"
            job["worker_id"] = idle_id
            job["assigned_at"] = time.time()

            msg = {
                "type": "assign_job",
                "job": {
                    "job_id": job["id"],
                    "kind": job["kind"],
                    "payload": job["payload"],
                    "limits": job["limits"],
                },
            }

            # send assignment (if it fails, revert and stop)
            try:
                await worker["ws"].send(json.dumps(msg))
            except Exception:
                worker["status"] = "idle"
                job["status"] = "queued"
                job["worker_id"] = None
                await job_queue.put(job_id)
                return


# -------------------- WEBSOCKET (WORKERS) --------------------

async def handle_worker(ws: WebSocketServerProtocol):
    worker_id: Optional[str] = None

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            t = msg.get("type")

            # register worker
            if t == "hello":
                worker_id = msg.get("worker_id") or str(uuid.uuid4())
                caps = msg.get("caps", {"cpu_cores": None, "gpu": False})

                async with lock:
                    workers[worker_id] = {
                        "ws": ws,
                        "status": "idle",
                        "caps": caps,
                        "last_seen": time.time(),
                    }

                await ws.send(json.dumps({"type": "hello_ack", "worker_id": worker_id}))
                await dispatch()
                continue

            if not worker_id:
                continue  # ignore anything before hello

            # update last_seen
            async with lock:
                if worker_id in workers:
                    workers[worker_id]["last_seen"] = time.time()

            if t == "hb":
                continue

            if t == "job_started":
                job_id = msg.get("job_id")
                async with lock:
                    job = jobs.get(job_id)
                    if job:
                        job["status"] = "running"
                        job["started_at"] = time.time()
                continue

            if t == "job_log":
                job_id = msg.get("job_id")
                line = msg.get("line", "")
                async with lock:
                    job = jobs.get(job_id)
                    if job:
                        job["logs"].append(line)
                        if len(job["logs"]) > 2000:
                            job["logs"] = job["logs"][-2000:]
                continue

            if t == "job_result":
                job_id = msg.get("job_id")
                async with lock:
                    job = jobs.get(job_id)
                    if job:
                        job["status"] = "completed"
                        job["finished_at"] = time.time()
                        job["result"] = {
                            "exit_code": msg.get("exit_code"),
                            "stdout": msg.get("stdout", ""),
                            "stderr": msg.get("stderr", ""),
                            "artifacts": msg.get("artifacts", []),
                        }

                    if worker_id in workers:
                        workers[worker_id]["status"] = "idle"

                await dispatch()
                continue

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if worker_id:
            async with lock:
                workers.pop(worker_id, None)


async def ws_router(ws: WebSocketServerProtocol):
    if ws.path != "/ws/worker":
        await ws.close(code=1008, reason="Invalid path")
        return
    await handle_worker(ws)


async def run_ws():
    print("WS workers: ws://0.0.0.0:8080/ws/worker")
    async with websockets.serve(ws_router, "0.0.0.0", 8080, max_size=10 * 1024 * 1024):
        await asyncio.Future()


# -------------------- HTTP API (USERS) --------------------

app = FastAPI(title="Grid-X Coordinator (Simple MVP)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/jobs")
async def submit_job(body: Dict[str, Any]):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "kind": body.get("kind", "python"),
        "payload": body.get("payload", {}),  # expects {"script": "..."}
        "limits": body.get("limits", {"cpus": 1, "memory": "256m", "timeout_s": 30}),
        "status": "queued",
        "worker_id": None,
        "created_at": time.time(),
        "assigned_at": None,
        "started_at": None,
        "finished_at": None,
        "logs": [],
        "result": None,
    }

    async with lock:
        jobs[job_id] = job
        await job_queue.put(job_id)

    await dispatch()
    return {"job_id": job_id}

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    async with lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

@app.get("/workers")
async def get_workers():
    async with lock:
        return [
            {"id": wid, "status": w["status"], "caps": w["caps"], "last_seen": w["last_seen"]}
            for wid, w in workers.items()
        ]


# -------------------- MAIN --------------------

async def main():
    ws_task = asyncio.create_task(run_ws())

    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="info")
    server = uvicorn.Server(config)
    http_task = asyncio.create_task(server.serve())

    await asyncio.gather(ws_task, http_task)

if __name__ == "__main__":
    asyncio.run(main())
