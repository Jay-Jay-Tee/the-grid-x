"""
Grid-X Worker - Run on one or more machines; connect to coordinator via COORDINATOR_WS.
Set COORDINATOR_WS=ws://<coordinator-host>:8080/ws/worker when coordinator is on another machine.
"""

import asyncio
import json
import os
import uuid
from typing import Optional

import websockets

from docker_manager import DockerManager
from task_queue import TaskQueue
from task_executor import TaskExecutor
from ws_worker_adapter import handle_assign_job
from resource_monitor import ResourceMonitor

# Coordinator WebSocket URL. When coordinator runs on another machine, set e.g.:
COORDINATOR_WS="ws://192.168.42.38:8080/ws/worker"
#   or COORDINATOR_WS=ws://coordinator.example.com:8080/ws/worker
#   COORDINATOR_WS = os.getenv("COORDINATOR_WS", "ws://localhost:8080/ws/worker")

# Optional: user_id that receives credits when this worker runs jobs (owner of this machine)
WORKER_OWNER_ID = os.getenv("WORKER_OWNER_ID", "")

# Docker socket: leave unset on Linux to use default /var/run/docker.sock;
# on Windows default is npipe; override with GRIDX_DOCKER_SOCKET or DOCKER_HOST if needed.
def _docker_socket() -> Optional[str]:
    if os.getenv("GRIDX_DOCKER_SOCKET"):
        return os.getenv("GRIDX_DOCKER_SOCKET")
    if os.getenv("DOCKER_HOST"):
        return os.getenv("DOCKER_HOST")
    if os.name == "nt":
        return "npipe:////./pipe/docker_engine"
    return None


async def worker_loop() -> None:
    worker_id = str(uuid.uuid4())
    docker_socket = _docker_socket()
    docker_manager = DockerManager(docker_socket=docker_socket)
    task_queue = TaskQueue()
    executor = TaskExecutor(docker_manager, task_queue)
    asyncio.create_task(executor.start_executor())

    # Optional: use resource monitor for accurate caps
    monitor = ResourceMonitor()
    caps = {"cpu_cores": monitor.get_cpu_metrics().get("cores", os.cpu_count() or 0), "gpu": False}
    gpu = monitor.get_gpu_metrics()
    if gpu and gpu.get("count", 0) > 0:
        caps["gpu"] = True

    while True:
        try:
            async with websockets.connect(
                COORDINATOR_WS,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                await ws.send(json.dumps({
                    "type": "hello",
                    "worker_id": worker_id,
                    "owner_id": WORKER_OWNER_ID.strip() or None,
                    "caps": caps,
                }))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    t = msg.get("type")
                    if not t:
                        continue

                    if t == "hello_ack":
                        worker_id = msg.get("worker_id", worker_id)
                        continue

                    if t == "assign_job":
                        await ws.send(json.dumps({
                            "type": "job_started",
                            "job_id": msg["job"]["job_id"],
                        }))
                        await handle_assign_job(msg, ws, executor, task_queue)
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"Disconnected from coordinator: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Worker error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(worker_loop())
