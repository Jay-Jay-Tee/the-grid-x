import os
import uuid
import time
import requests

import asyncio
import json
import os
import uuid
import websockets

from docker_manager import DockerManager
from task_queue import TaskQueue
from task_executor import TaskExecutor
from ws_worker_adapter import handle_assign_job
from resource_monitor import ResourceMonitor

COORDINATOR_WS = "ws://192.168.42.38:8081/ws"

# COORDINATOR_WS = os.getenv("COORDINATOR_WS", "ws://192.168.42.38/ws")

async def worker_loop():
    worker_id = str(uuid.uuid4())

    docker_manager = DockerManager(docker_socket="npipe:////./pipe/docker_engine")
    task_queue = TaskQueue()
    executor = TaskExecutor(docker_manager, task_queue)
    # Start executor loop in background to process enqueued tasks
    asyncio.create_task(executor.start_executor())

    async with websockets.connect(COORDINATOR_WS) as ws:
        await ws.send("hello_from_worker")
        reply = await ws.recv()
        print("COORDINATOR SAYS:", reply)
        # Say hello
        await ws.send(json.dumps({
            "type": "hello",
            "worker_id": worker_id,
            "caps": {
                "cpu_cores": os.cpu_count(),
                "gpu": False
            }
        }))

        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            t = msg.get("type")
            if not t:
                continue

            if t == "assign_job":
                await ws.send(json.dumps({
                    "type": "job_started",
                    "job_id": msg["job"]["job_id"]
                }))

                await handle_assign_job(msg, ws, executor, task_queue)


if __name__ == "__main__":
    asyncio.run(worker_loop())
