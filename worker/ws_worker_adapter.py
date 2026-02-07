# ws_worker_adapter.py
import asyncio
import json
from task_queue import Task, TaskQueue, TaskPriority, TaskStatus
from task_executor import TaskExecutor

async def handle_assign_job(msg, ws, executor: TaskExecutor, queue: TaskQueue):
    """Enqueue the job and monitor completion, sending result back over the websocket.

    This function enqueues the task and returns quickly. A background coroutine
    monitors the `TaskQueue` for completion and sends the `job_result` message
    when available.
    """
    job = msg["job"]

    task = Task(
        task_id=job["job_id"],
        code=job["payload"]["script"],
        language=job["kind"],
        requirements={"cpu": {"cores": 1}},
        priority=TaskPriority.NORMAL,
        timeout=job["limits"].get("timeout_s", 30)
    )

    await queue.enqueue(task)

    async def _monitor_and_send(tid: str):
        # Poll the queue for task status changes; when completed/failed/cancelled, send result
        while True:
            t = queue.get_task(tid)
            if t is None:
                await asyncio.sleep(0.5)
                continue

            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                stdout = ""
                stderr = ""
                exit_code = 0

                if t.status == TaskStatus.COMPLETED:
                    stdout = (t.result or {}).get('output', '')
                else:
                    stderr = t.error or (t.result or {}).get('error', '')
                    exit_code = 1

                await ws.send(json.dumps({
                    "type": "job_result",
                    "job_id": tid,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                }))
                return

            await asyncio.sleep(0.5)

    # Start background monitor (don't await) so we return quickly to the websocket loop
    asyncio.create_task(_monitor_and_send(task.task_id))