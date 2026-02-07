"""
Grid-X Hybrid Worker - Run as both worker (earn credits) and client (submit jobs).
This is the default way to participate in Grid-X network.

Usage:
  # Interactive mode (worker + CLI)
  python -m worker.main --user alice
  
  # Worker-only mode (background service)
  python -m worker.main --user alice --no-cli
  
  # Specify coordinator
  python -m worker.main --user alice --coordinator-ip 192.168.1.100
"""

import asyncio
import json
import os
import sys
import uuid
from typing import Optional
import argparse

import websockets
import requests

from docker_manager import DockerManager
from task_queue import TaskQueue
from task_executor import TaskExecutor
from ws_worker_adapter import handle_assign_job
from resource_monitor import ResourceMonitor


class HybridWorker:
    """Worker that also provides client CLI functionality."""
    
    def __init__(self, user_id: str, coordinator_ip: str = "localhost", 
                 http_port: int = 8081, ws_port: int = 8080):
        self.user_id = user_id
        self.coordinator_http = f"http://{coordinator_ip}:{http_port}"
        self.coordinator_ws = f"ws://{coordinator_ip}:{ws_port}/ws/worker"
        
        print(f"🚀 Grid-X Hybrid Worker-Client")
        print(f"   User: {user_id}")
        print(f"   Coordinator HTTP: {self.coordinator_http}")
        print(f"   Coordinator WS: {self.coordinator_ws}")
        print()
    
    async def run_worker(self):
        """Run the worker loop - connects to coordinator and executes jobs."""
        worker_id = str(uuid.uuid4())
        
        # Docker setup
        def _docker_socket() -> Optional[str]:
            if os.getenv("GRIDX_DOCKER_SOCKET"):
                return os.getenv("GRIDX_DOCKER_SOCKET")
            if os.getenv("DOCKER_HOST"):
                return os.getenv("DOCKER_HOST")
            if os.name == "nt":
                return "npipe:////./pipe/docker_engine"
            return None
        
        docker_socket = _docker_socket()
        docker_manager = DockerManager(docker_socket=docker_socket)
        task_queue = TaskQueue()
        executor = TaskExecutor(docker_manager, task_queue)
        asyncio.create_task(executor.start_executor())
        
        # Get system capabilities
        monitor = ResourceMonitor()
        caps = {
            "cpu_cores": monitor.get_cpu_metrics().get("cores", os.cpu_count() or 0),
            "gpu": False
        }
        gpu = monitor.get_gpu_metrics()
        if gpu and gpu.get("count", 0) > 0:
            caps["gpu"] = True
        
        print(f"👷 Starting worker process...")
        print(f"   Owner: {self.user_id} (you'll earn credits when this runs jobs)")
        print(f"   Capabilities: {caps['cpu_cores']} CPU cores, GPU: {caps['gpu']}")
        print()
        
        # Worker connection loop
        while True:
            try:
                async with websockets.connect(
                    self.coordinator_ws,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    await ws.send(json.dumps({
                        "type": "hello",
                        "worker_id": worker_id,
                        "owner_id": self.user_id,
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
    
    # Client functionality methods
    def submit_job(self, code: str, wait_for_result: bool = True) -> Optional[str]:
        """Submit a job as a client."""
        try:
            response = requests.post(
                f"{self.coordinator_http}/jobs",
                json={
                    "user_id": self.user_id,
                    "code": code,
                    "language": "python"
                },
                timeout=10
            )
            
            if response.status_code == 402:
                print(f"❌ Insufficient credits!")
                self.check_credits()
                return None
            
            response.raise_for_status()
            job_id = response.json()["job_id"]
            print(f"✅ Job submitted: {job_id}")
            
            if wait_for_result:
                self._wait_for_job(job_id)
            
            return job_id
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to coordinator at {self.coordinator_http}")
            return None
        except Exception as e:
            print(f"❌ Error submitting job: {e}")
            return None
    
    def _wait_for_job(self, job_id: str):
        """Poll job status until completion."""
        import time
        print(f"⏳ Waiting for job {job_id}...")
        
        while True:
            try:
                response = requests.get(
                    f"{self.coordinator_http}/jobs/{job_id}",
                    timeout=10
                )
                response.raise_for_status()
                job = response.json()
                
                status = job["status"]
                if status in ["completed", "failed"]:
                    print(f"\n{'='*60}")
                    print(f"Job {status.upper()}")
                    print(f"{'='*60}")
                    
                    if job.get('stdout'):
                        print(f"Output:\n{job['stdout']}")
                    if job.get('stderr'):
                        print(f"Errors:\n{job['stderr']}")
                    print(f"{'='*60}\n")
                    break
                
                time.sleep(2)
            except Exception as e:
                print(f"❌ Error checking job: {e}")
                break
    
    def check_credits(self):
        """Check and display credit balance."""
        try:
            response = requests.get(
                f"{self.coordinator_http}/credits/{self.user_id}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            balance = data['balance']
            
            print(f"💰 Balance: {balance:.2f} credits")
            
            if balance < 1.0:
                print(f"⚠️  Low balance! Keep your worker running to earn more.")
            
        except Exception as e:
            print(f"❌ Error checking credits: {e}")
    
    def list_workers(self):
        """List all registered workers in the network."""
        try:
            response = requests.get(f"{self.coordinator_http}/workers", timeout=10)
            response.raise_for_status()
            workers = response.json()
            
            print(f"\n🖥️  Workers in network: {len(workers)}")
            for w in workers:
                status_emoji = "✅" if w['status'] == 'idle' else "🔄"
                owner = w.get('owner_id', 'unknown')
                you = " (YOU)" if owner == self.user_id else ""
                print(f"  {status_emoji} {w['id'][:12]}... - {w['status']} - Owner: {owner}{you}")
            print()
            
        except Exception as e:
            print(f"❌ Error listing workers: {e}")


async def run_interactive_cli(worker: HybridWorker):
    """Run interactive CLI for job submission while worker runs in background."""
    print(f"💬 Interactive Mode")
    print(f"   Commands: submit <code> | file <path> | credits | workers | help | quit")
    print(f"   Your worker is running in the background earning credits!\n")
    
    while True:
        try:
            cmd = await asyncio.to_thread(input, f"{worker.user_id}> ")
            cmd = cmd.strip()
            
            if not cmd:
                continue
            
            if cmd == "quit" or cmd == "exit":
                print("👋 Shutting down...")
                break
            
            elif cmd == "credits":
                worker.check_credits()
            
            elif cmd == "workers":
                worker.list_workers()
            
            elif cmd == "help":
                print("""
Commands:
  submit <code>     Submit Python code (e.g., submit print('hello'))
  file <path>       Submit code from file (e.g., file script.py)
  credits           Check your credit balance
  workers           List all workers in network
  help              Show this help
  quit              Exit
                """)
            
            elif cmd.startswith("submit "):
                code = cmd[7:].strip()
                if code:
                    worker.submit_job(code)
                else:
                    print("❌ No code provided")
            
            elif cmd.startswith("file "):
                filepath = cmd[5:].strip()
                try:
                    with open(filepath, 'r') as f:
                        code = f.read()
                    worker.submit_job(code)
                except FileNotFoundError:
                    print(f"❌ File not found: {filepath}")
                except Exception as e:
                    print(f"❌ Error reading file: {e}")
            
            else:
                print(f"❌ Unknown command: {cmd}")
                print(f"   Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            break
        except EOFError:
            break


async def main():
    parser = argparse.ArgumentParser(
        description="Grid-X Hybrid Worker - Earn credits as worker, submit jobs as client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python -m worker.main --user alice
  
  # With remote coordinator
  python -m worker.main --user alice --coordinator-ip 192.168.1.100
  
  # Worker-only mode (no CLI, background service)
  python -m worker.main --user alice --no-cli
        """
    )
    
    parser.add_argument("--user", required=True,
                       help="Your user ID (for credit tracking)")
    parser.add_argument("--coordinator-ip", default="localhost",
                       help="IP address of coordinator (default: localhost)")
    parser.add_argument("--http-port", type=int, default=8081,
                       help="Coordinator HTTP port (default: 8081)")
    parser.add_argument("--ws-port", type=int, default=8080,
                       help="Coordinator WebSocket port (default: 8080)")
    parser.add_argument("--no-cli", action="store_true",
                       help="Run only as worker (no interactive CLI)")
    
    args = parser.parse_args()
    
    # Create hybrid worker
    worker = HybridWorker(
        user_id=args.user,
        coordinator_ip=args.coordinator_ip,
        http_port=args.http_port,
        ws_port=args.ws_port
    )
    
    if args.no_cli:
        # Just run worker (blocking)
        await worker.run_worker()
    else:
        # Run worker in background + interactive CLI
        worker_task = asyncio.create_task(worker.run_worker())
        
        # Give worker a moment to start
        await asyncio.sleep(2)
        
        try:
            await run_interactive_cli(worker)
        finally:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")