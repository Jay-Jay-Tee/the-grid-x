"""
Grid-X Hybrid Worker - Run as both worker (earn credits) and client (submit jobs).
This is the default way to participate in Grid-X network.

Usage:
  # Interactive mode (worker + CLI)
  python -m worker.main --user alice --password yourpass
  
  # Worker-only mode (background service)
  python -m worker.main --user alice --password yourpass --no-cli
  
  # Specify coordinator
  python -m worker.main --user alice --password yourpass --coordinator-ip 192.168.1.100
"""

import asyncio
import json
import os
import sys
import uuid
import hashlib
from pathlib import Path
from typing import Optional
import argparse
import time

import websockets
import requests
from websockets import exceptions as ws_exceptions

from .docker_manager import DockerManager
from .task_queue import TaskQueue
from .task_executor import TaskExecutor
from .ws_worker_adapter import handle_assign_job
from .resource_monitor import ResourceMonitor


class WorkerIdentity:
    """Manages persistent worker identity and authentication."""
    
    def __init__(self, user_id: str, password: str):
        self.user_id = user_id
        self.password = password
        self.config_dir = Path.home() / ".gridx"
        self.config_file = self.config_dir / f"worker_{user_id}.json"
        self.worker_id = None
        self.auth_token = None
        
    def _hash_credentials(self) -> str:
        """Create auth token from username and password."""
        combined = f"{self.user_id}:{self.password}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def load_or_create_identity(self) -> dict:
        """Load existing worker identity or create new one."""
        self.auth_token = self._hash_credentials()
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing identity
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    stored_user_id = data.get('user_id')
                    
                    # If username matches, always use the existing worker_id
                    # The server will validate the password
                    if stored_user_id == self.user_id:
                        self.worker_id = data.get('worker_id')
                        # Update auth token in case password changed
                        data['auth_token'] = self.auth_token
                        data['last_used'] = time.time()
                        
                        # Save updated data
                        with open(self.config_file, 'w') as f_write:
                            json.dump(data, f_write, indent=2)
                        
                        print(f"✓ Loaded existing worker identity")
                        print(f"  Worker ID: {self.worker_id[:16]}...")
                        return data
            except Exception as e:
                print(f"⚠️  Error loading identity: {e}")
        
        # Create new identity (only for brand new users)
        self.worker_id = str(uuid.uuid4())
        data = {
            'worker_id': self.worker_id,
            'user_id': self.user_id,
            'auth_token': self.auth_token,
            'created_at': time.time(),
            'last_used': time.time()
        }
        
        # Save to file
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Created new worker identity")
        print(f"  Worker ID: {self.worker_id[:16]}...")
        
        return data
    
    def get_worker_id(self) -> str:
        """Get the persistent worker ID."""
        if not self.worker_id:
            self.load_or_create_identity()
        return self.worker_id
    
    def get_auth_token(self) -> str:
        """Get the authentication token."""
        if not self.auth_token:
            self.auth_token = self._hash_credentials()
        return self.auth_token


class ActivityLogger:
    """Logs recent worker activity in privacy-preserving format."""
    
    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self.log = []
    
    def add_entry(self, event_type: str, details: str = ""):
        """Add a log entry with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            'timestamp': timestamp,
            'type': event_type,
            'details': details
        }
        self.log.append(entry)
        
        # Keep only most recent entries
        if len(self.log) > self.max_entries:
            self.log = self.log[-self.max_entries:]
    
    def get_recent(self, count: int = 10) -> list:
        """Get recent log entries."""
        return self.log[-count:]
    
    def display_recent(self, count: int = 10):
        """Display recent activity."""
        entries = self.get_recent(count)
        if not entries:
            print("No recent activity")
            return
        
        print(f"\n📋 Recent Activity (last {len(entries)} events):")
        print("-" * 60)
        for entry in entries:
            print(f"[{entry['timestamp']}] {entry['type']}")
            if entry['details']:
                print(f"  └─ {entry['details']}")
        print("-" * 60 + "\n")


class HybridWorker:
    """Worker that also provides client CLI functionality."""
    
    def __init__(self, user_id: str, password: str, coordinator_ip: str = "localhost", 
                 http_port: int = 8081, ws_port: int = 8080):
        self.user_id = user_id
        self.coordinator_http = f"http://{coordinator_ip}:{http_port}"
        self.coordinator_ws = f"ws://{coordinator_ip}:{ws_port}/ws/worker"
        
        # Identity management
        self.identity = WorkerIdentity(user_id, password)
        self.identity.load_or_create_identity()
        
        # Activity logging
        self.activity_log = ActivityLogger()
        
        # Connection state
        self.is_connected = False
        self.last_heartbeat = 0
        self.connection_attempts = 0
        
        print(f"\n🚀 Grid-X Hybrid Worker-Client")
        print(f"   User: {user_id}")
        print(f"   Coordinator HTTP: {self.coordinator_http}")
        print(f"   Coordinator WS: {self.coordinator_ws}")
        print()
    
    def _check_coordinator_connection(self) -> bool:
        """Check if coordinator is reachable."""
        try:
            response = requests.get(f"{self.coordinator_http}/workers", timeout=2)
            return response.status_code in [200, 201]
        except Exception:
            return False
    
    async def run_worker(self):
        """Run the worker loop - connects to coordinator and executes jobs."""
        try:
            worker_id = self.identity.get_worker_id()
            auth_token = self.identity.get_auth_token()
            
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
            
            # Only start executor if Docker is available
            if docker_manager.available:
                asyncio.create_task(executor.start_executor())
            else:
                print(f"⚠️  Docker is not available. Worker will connect but cannot execute tasks.")
                print(f"   To enable task execution, start Docker Desktop (Windows/Mac) or Docker daemon (Linux).")
            
            # Get system capabilities
            monitor = ResourceMonitor()
            caps = {
                "cpu_cores": monitor.get_cpu_metrics().get("cores", os.cpu_count() or 0),
                "gpu": False
            }
            gpu = monitor.get_gpu_metrics()
            if gpu and gpu.get("count", 0) > 0:
                caps["gpu"] = True
            # Indicate whether this worker can actually execute tasks (Docker available)
            caps["can_execute"] = docker_manager.available
            
            print(f"👷 Starting worker process...")
            print(f"   Worker ID: {worker_id[:16]}...")
            print(f"   Owner: {self.user_id}")
            print(f"   Capabilities: {caps['cpu_cores']} CPU cores, GPU: {caps['gpu']}")
            print(f"   Docker: {'✅ Available' if docker_manager.available else '❌ Not available'}")
            print()
            
            # Worker connection loop
            reconnect_delay = 5
            max_reconnect_delay = 60
            
            while True:
                try:
                    # Check if coordinator is reachable before connecting
                    if not self._check_coordinator_connection():
                        self.is_connected = False
                        self.connection_attempts += 1
                        
                        if self.connection_attempts == 1:
                            print(f"❌ Cannot reach coordinator at {self.coordinator_http}")
                            print(f"   Retrying every {reconnect_delay}s...")
                            self.activity_log.add_entry("Connection Failed", "Coordinator unreachable")
                        
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                        continue
                
                # Reset reconnect delay on successful ping
                reconnect_delay = 5
                
                async with websockets.connect(
                    self.coordinator_ws,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=15,
                ) as ws:
                    # Send hello with authentication
                    try:
                        await ws.send(json.dumps({
                            "type": "hello",
                            "worker_id": worker_id,
                            "owner_id": self.user_id,
                            "auth_token": auth_token,
                            "caps": caps,
                        }))
                        
                        # Wait for acknowledgment (increased timeout to allow coordinator more time)
                        ack_msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        ack = json.loads(ack_msg)
                    except asyncio.TimeoutError:
                        print(f"⚠️  Handshake timeout - coordinator not responding within 30 seconds")
                        self.activity_log.add_entry("Timeout", "Handshake timeout with coordinator")
                        await asyncio.sleep(reconnect_delay)
                        continue
                    except Exception as e:
                        print(f"⚠️  Error during handshake: {e}")
                        self.activity_log.add_entry("Handshake Error", str(e)[:50])
                        await asyncio.sleep(reconnect_delay)
                        continue
                    
                    # Check for authentication error
                    if ack.get("type") == "auth_error":
                        print(f"\n{'='*60}")
                        print(f"❌ AUTHENTICATION FAILED")
                        print(f"{'='*60}")
                        print(f"\n{ack.get('error', 'Invalid credentials')}\n")
                        print(f"This username already exists with a different password.")
                        print(f"Please use the correct password or choose a different username.")
                        print(f"\n{'='*60}\n")
                        self.activity_log.add_entry("Auth Failed", ack.get('error', 'Invalid credentials'))
                        # Raise exception to trigger cleanup and prevent CLI from starting
                        raise RuntimeError("Authentication failed - invalid credentials")
                    
                    if ack.get("type") == "hello_ack":
                        if not self.is_connected:
                            print(f"✅ Connected to coordinator")
                            print(f"   You're now earning credits when jobs run on your worker!\n")
                            self.activity_log.add_entry("Connected", "Worker registered with coordinator")
                        
                        self.is_connected = True
                        self.connection_attempts = 0
                        self.last_heartbeat = time.time()

                        # Start periodic heartbeat to coordinator to keep DB last_heartbeat fresh
                        async def _hb_loop(ws, interval: int = 10):
                            try:
                                while True:
                                    await asyncio.sleep(interval)
                                    try:
                                        await ws.send(json.dumps({"type": "hb", "ts": time.time()}))
                                    except Exception:
                                        return
                            except asyncio.CancelledError:
                                return

                        hb_task = asyncio.create_task(_hb_loop(ws))
                        
                        # Handle messages
                        async for raw in ws:
                            try:
                                msg = json.loads(raw)
                            except Exception:
                                continue
                            
                            t = msg.get("type")
                            if not t:
                                continue
                            
                            # Update heartbeat
                            self.last_heartbeat = time.time()
                            
                            if t == "hello_ack":
                                continue
                            
                            if t == "assign_job":
                                job_id = msg["job"]["job_id"]
                                self.activity_log.add_entry("Job Assigned", f"ID: {job_id[:8]}...")
                                
                                await ws.send(json.dumps({
                                    "type": "job_started",
                                    "job_id": job_id,
                                }))
                                
                                await handle_assign_job(msg, ws, executor, task_queue)
                                self.activity_log.add_entry("Job Completed", f"ID: {job_id[:8]}...")
                        
                        # Ensure heartbeat task is cancelled when websocket context exits
                        try:
                            if 'hb_task' in locals() and hb_task is not None:
                                hb_task.cancel()
                        except Exception:
                            pass
                    else:
                        print(f"❌ Invalid response from coordinator during handshake: {ack.get('type')}")
                        self.activity_log.add_entry("Handshake Error", f"Invalid response: {ack.get('type')}")
                        await asyncio.sleep(30)
                        
            except ws_exceptions.ConnectionClosed as e:
                self.is_connected = False
                if self.connection_attempts == 0:
                    print(f"⚠️  Disconnected from coordinator. Reconnecting...")
                    self.activity_log.add_entry("Disconnected", "Connection closed")
                await asyncio.sleep(reconnect_delay)
                self.connection_attempts += 1
                
            except (ConnectionRefusedError, OSError) as e:
                self.is_connected = False
                if self.connection_attempts == 0:
                    print(f"❌ Cannot connect to coordinator: {e}")
                    print(f"   Retrying every {reconnect_delay}s...")
                    self.activity_log.add_entry("Connection Error", str(e)[:50])
                await asyncio.sleep(reconnect_delay)
                self.connection_attempts += 1
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                
            except asyncio.TimeoutError:
                self.is_connected = False
                print(f"⚠️  Connection timeout. Retrying...")
                self.activity_log.add_entry("Timeout", "No response from coordinator")
                await asyncio.sleep(reconnect_delay)
                
            except RuntimeError as e:
                # Authentication failure - do not retry
                if "Authentication failed" in str(e):
                    self.is_connected = False
                    return  # Exit gracefully
                else:
                    # Other runtime errors - retry
                    self.is_connected = False
                    print(f"❌ Runtime error: {e}. Reconnecting...")
                    self.activity_log.add_entry("Error", str(e)[:50])
                    await asyncio.sleep(reconnect_delay)
                
            except Exception as e:
                self.is_connected = False
                print(f"❌ Worker error: {e}. Reconnecting...")
                self.activity_log.add_entry("Error", str(e)[:50])
                await asyncio.sleep(reconnect_delay)
        
        except Exception as e:
            print(f"\n❌ FATAL ERROR IN WORKER PROCESS:")
            print(f"{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.is_connected = False
            self.activity_log.add_entry("Fatal Error", f"{type(e).__name__}: {str(e)[:50]}")
    
    # Client functionality methods
    def submit_job(self, code: str, wait_for_result: bool = True) -> Optional[str]:
        """Submit a job as a client."""
        
        # Check connection status first
        if not self.is_connected:
            print(f"❌ Not connected to coordinator - cannot submit job")
            print(f"   Your worker is not earning credits or able to submit jobs.")
            print(f"   Type 'status' to check connection or wait for reconnection.")
            return None
        
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
            self.activity_log.add_entry("Job Submitted", f"ID: {job_id[:8]}...")
            
            if wait_for_result:
                self._wait_for_job(job_id)
            
            return job_id
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to coordinator at {self.coordinator_http}: {e}")
            print("   Check network, firewall, or the --coordinator-ip value.")
            return None
        except requests.exceptions.Timeout:
            print(f"⚠️  Coordinator timed out at {self.coordinator_http}. Try again later.")
            return None
        except requests.exceptions.HTTPError as e:
            # Attempt to include response text for more context
            resp_text = None
            try:
                resp_text = response.text
            except Exception:
                resp_text = ''
            print(f"❌ HTTP error submitting job: {e}. {resp_text}")
            return None
        except Exception as e:
            print(f"❌ Error submitting job: {repr(e)}")
            return None
    
    def _wait_for_job(self, job_id: str):
        """Poll job status until completion."""
        import time
        print(f"⏳ Waiting for job {job_id}...")
        # Use time-based polling with exponential backoff on errors to avoid
        # noisy logs when the coordinator is temporarily unreachable.
        timeout_seconds = 60 * 10  # 10 minutes
        start = time.time()
        last_status = "queued"

        backoff = 2.0
        max_backoff = 30.0
        consecutive_errors = 0

        while time.time() - start < timeout_seconds:
            try:
                response = requests.get(
                    f"{self.coordinator_http}/jobs/{job_id}",
                    timeout=10
                )
                response.raise_for_status()
                job = response.json()

                # Reset error/backoff state on success
                consecutive_errors = 0
                backoff = 2.0

                status = job.get("status")

                # Report status change
                if status != last_status:
                    print(f"📊 Job status: {status}")
                    last_status = status

                if status in ["completed", "failed", "error"]:
                    print(f"\n{'='*60}")
                    print(f"✅ Job {status.upper()}")
                    print(f"{'='*60}")

                    if job.get('stdout'):
                        print(f"📤 Output:\n{job['stdout']}")
                    if job.get('stderr'):
                        print(f"❌ Errors:\n{job['stderr']}")
                    if job.get('exit_code') is not None:
                        print(f"Exit code: {job['exit_code']}")
                    print(f"{'='*60}\n")
                    return

                # Regular polling interval when coordinator is reachable
                time.sleep(2)

            except requests.exceptions.RequestException as e:
                # First error: show a clear warning. Subsequent errors: quieter,
                # but still inform occasionally to indicate continued problems.
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print(f"⚠️  Error checking job: {e} — will retry with backoff")
                elif consecutive_errors % 5 == 0:
                    print(f"⚠️  Still having issues checking job (attempt #{consecutive_errors}): {e}")

                # Sleep with exponential backoff and small jitter
                sleep_time = backoff + (0.1 * (os.getpid() % 5))
                time.sleep(sleep_time)
                backoff = min(backoff * 1.5, max_backoff)

            except Exception as e:
                # Catch-all for unexpected errors
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print(f"⚠️  Unexpected error checking job: {e}")
                elif consecutive_errors % 5 == 0:
                    print(f"⚠️  Repeated unexpected errors (#{consecutive_errors}): {e}")
                time.sleep(min(backoff, max_backoff))
                backoff = min(backoff * 1.5, max_backoff)

        # Timeout expired
        print(f"\n❌ Job polling timeout after {timeout_seconds//60} minutes")
        print(f"   The job may still be executing on a remote worker")
        print(f"   Check status with: GET /jobs/{job_id}")
    
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
            
            my_worker_id = self.identity.get_worker_id()
            
            print(f"\n🖥️  Workers in network: {len(workers)}")
            for w in workers:
                status_emoji = "✅" if w['status'] == 'idle' else ("🔄" if w['status'] == 'busy' else "⚫")
                owner = w.get('owner_id', 'unknown')
                is_you = " (YOU)" if w['id'] == my_worker_id else ""
                print(f"  {status_emoji} {w['id'][:12]}... - {w['status']} - Owner: {owner}{is_you}")
            print()
            
        except Exception as e:
            print(f"❌ Error listing workers: {e}")
    
    def show_status(self):
        """Show worker connection status."""
        status = "🟢 CONNECTED" if self.is_connected else "🔴 DISCONNECTED"
        print(f"\n{status}")
        print(f"Worker ID: {self.identity.get_worker_id()[:16]}...")
        print(f"User: {self.user_id}")
        if self.is_connected:
            elapsed = time.time() - self.last_heartbeat
            print(f"Last heartbeat: {elapsed:.1f}s ago")
            print(f"Status: Earning credits ✅")
        else:
            print(f"Status: Not earning credits (disconnected)")
        print()


async def run_interactive_cli(worker: HybridWorker):
    """Run interactive CLI for job submission while worker runs in background."""
    print(f"💬 Interactive Mode")
    print(f"   Commands: submit <code> | file <path> | credits | workers | status | log | help | quit")
    
    # Show initial status
    await asyncio.sleep(3)  # Give worker time to connect
    worker.show_status()
    
    # Track disconnection warnings
    last_disconnection_warning = 0
    
    while True:
        try:
            # Check if worker lost connection and warn periodically
            if not worker.is_connected:
                current_time = time.time()
                # Show warning every 30 seconds to avoid spam
                if current_time - last_disconnection_warning > 30:
                    print(f"\n⚠️  Lost connection to coordinator!")
                    print(f"   Worker is attempting to reconnect...")
                    print(f"   Type 'status' to check or 'quit' to exit.\n")
                    last_disconnection_warning = current_time
            
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
            
            elif cmd == "status":
                worker.show_status()
            
            elif cmd == "log":
                worker.activity_log.display_recent(15)
            
            elif cmd == "help":
                print("""
Commands:
  submit <code>     Submit Python code (e.g., submit print('hello'))
  file <path>       Submit code from file (e.g., file script.py)
  credits           Check your credit balance
  workers           List all workers in network
  status            Show worker connection status
  log               Show recent activity log
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
  python -m worker.main --user alice --password mypass123
  
  # With remote coordinator
  python -m worker.main --user alice --password mypass123 --coordinator-ip 192.168.1.100
  
  # Worker-only mode (no CLI, background service)
  python -m worker.main --user alice --password mypass123 --no-cli
        """
    )
    
    parser.add_argument("--user", required=True,
                       help="Your user ID (for credit tracking)")
    parser.add_argument("--password", required=True,
                       help="Your password (for authentication)")
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
        password=args.password,
        coordinator_ip=args.coordinator_ip,
        http_port=args.http_port,
        ws_port=args.ws_port
    )
    
    if args.no_cli:
        # Just run worker (blocking)
        try:
            await worker.run_worker()
        except RuntimeError as e:
            if "Authentication failed" in str(e):
                # Clean exit on auth failure
                pass
            else:
                raise
    else:
        # Run worker in background + interactive CLI
        worker_task = asyncio.create_task(worker.run_worker())
        
        # Give worker MORE time to complete initial connection/auth
        # Increased from 2 to 5 seconds to avoid race conditions
        await asyncio.sleep(5)
        
        # Check if worker task failed due to auth
        if worker_task.done():
            try:
                worker_task.result()
            except RuntimeError as e:
                if "Authentication failed" in str(e):
                    # Auth failed - DO NOT START CLI, exit completely
                    print("\n⚠️  Cannot start interactive mode - authentication failed")
                    print("Please check your username and password and try again.\n")
                    return  # Exit without starting CLI
                else:
                    raise
        
        # Verify worker is actually connected before starting CLI
        # This prevents CLI from starting if authentication is still in progress
        if not worker.is_connected:
            print("\n⚠️  Cannot start interactive mode - not connected to coordinator")
            print("Please check your coordinator address and try again.\n")
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            return
        
        # NOW it's safe to start CLI
        try:
            await run_interactive_cli(worker)
        finally:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            except RuntimeError as e:
                # Suppress auth failure errors during shutdown
                if "Authentication failed" not in str(e):
                    raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")