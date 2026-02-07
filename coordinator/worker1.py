# worker_docker.py
# Minimal Grid-X worker that executes received Python code INSIDE Docker.
#
# Requirements:
#   pip install websockets
#   Docker installed + running on worker laptop
#   Build the job image once on the worker:
#       docker pull python:3.11-slim
# (This worker just uses python:3.11-slim directly)
#
# Run:
#   python worker_docker.py --coordinator ws://<COORD_IP>:8080/ws/worker --worker-id w1
#
# Coordinator sends payload: {"script": "..."} (or {"script_b64":"..."} optionally)

import argparse
import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import websockets


def decode_script(payload: Dict[str, Any]) -> str:
    if "script" in payload and isinstance(payload["script"], str):
        return payload["script"]
    if "script_b64" in payload and isinstance(payload["script_b64"], str):
        return base64.b64decode(payload["script_b64"]).decode("utf-8", errors="replace")
    return "print('No script provided')\n"


def run_in_docker(
    script_text: str,
    limits: Dict[str, Any],
    work_root: Path,
) -> tuple[int, str, str]:
    """
    Write script to a per-job dir, run python inside a sandboxed docker container,
    return (exit_code, stdout, stderr).
    """
    job_id = uuid.uuid4().hex[:10]
    job_dir = work_root / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (input_dir / "main.py").write_text(script_text, encoding="utf-8")

    cpus = str(limits.get("cpus", 1))
    memory = str(limits.get("memory", "256m"))
    timeout_s = int(limits.get("timeout_s", 30))

    # Sandbox flags (MVP):
    # - read-only rootfs
    # - drop caps
    # - no-new-privileges
    # - no network
    # - run as non-root
    # - mount ONLY the per-job folder
    cmd = [
        "docker", "run", "--rm",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=256",
        f"--cpus={cpus}",
        f"--memory={memory}",
        "--network=none",
        "--user", "1000:1000",
        "--tmpfs", "/tmp:rw,size=128m",
        "-v", f"{str(input_dir)}:/work/input:ro",
        "-v", f"{str(output_dir)}:/work/output:rw",
        "python:3.11-slim",
        "python", "/work/input/main.py",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Timed out"
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def worker_loop(coordinator_ws: str, worker_id: str):
    work_root = Path("./gridx-work").resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            async with websockets.connect(coordinator_ws, max_size=10 * 1024 * 1024) as ws:
                # Register
                await ws.send(json.dumps({
                    "type": "hello",
                    "worker_id": worker_id,
                    "caps": {
                        "cpu_cores": os.cpu_count() or 1,
                        "gpu": False,
                        "docker": True,
                    }
                }))

                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") != "assign_job":
                        continue

                    job = msg.get("job") or {}
                    job_id = job.get("job_id")
                    kind = job.get("kind", "python")
                    payload = job.get("payload") or {}
                    limits = job.get("limits") or {}

                    if not job_id:
                        continue

                    # Start
                    await ws.send(json.dumps({"type": "job_started", "job_id": job_id}))

                    if kind != "python":
                        await ws.send(json.dumps({
                            "type": "job_result",
                            "job_id": job_id,
                            "exit_code": 2,
                            "stdout": "",
                            "stderr": f"Unsupported kind: {kind}",
                            "artifacts": [],
                        }))
                        continue

                    script = decode_script(payload)

                    exit_code, stdout, stderr = run_in_docker(script, limits, work_root)

                    await ws.send(json.dumps({
                        "type": "job_result",
                        "job_id": job_id,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "artifacts": [],
                    }))

        except Exception as e:
            print(f"[worker] disconnected, retrying: {e}", file=sys.stderr)
            await asyncio.sleep(2)


def main():
    # Set your coordinator LAN IP here
    COORDINATOR_WS = "ws://172.27.128.1:8080/ws/worker"

    WORKER_ID = "worker-1"

    asyncio.run(worker_loop(COORDINATOR_WS, WORKER_ID))


if __name__ == "__main__":
    main()
