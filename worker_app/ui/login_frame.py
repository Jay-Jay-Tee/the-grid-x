"""
Login screen - username, password, coordinator settings, Docker check.
"""

import sys
import os
import asyncio
import threading

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import customtkinter as ctk
from typing import Callable, Optional, Any


class LoginFrame(ctk.CTkFrame):
    """Login form with username, password, coordinator IP, and Docker check."""

    def __init__(
        self,
        parent,
        on_success: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_success = on_success
        self.worker = None
        self.worker_task = None
        self.loop = None
        self._thread = None
        self._check_after_id = None

        self._build_ui()

    def _build_ui(self):
        """Build the login form UI."""
        # Title
        title = ctk.CTkLabel(self, text="Grid-X Worker", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))

        # Username
        ctk.CTkLabel(self, text="Username").pack(anchor="w", pady=(5, 0))
        self._username = ctk.CTkEntry(self, placeholder_text="alice", width=300)
        self._username.pack(pady=(2, 10), fill="x")

        # Password
        ctk.CTkLabel(self, text="Password").pack(anchor="w", pady=(5, 0))
        self._password = ctk.CTkEntry(self, placeholder_text="••••••••", show="•", width=300)
        self._password.pack(pady=(2, 10), fill="x")

        # Coordinator IP (optional)
        ctk.CTkLabel(self, text="Coordinator IP (optional)").pack(anchor="w", pady=(5, 0))
        self._coordinator_ip = ctk.CTkEntry(self, placeholder_text="localhost", width=300)
        self._coordinator_ip.insert(0, "localhost")
        self._coordinator_ip.pack(pady=(2, 10), fill="x")

        # Docker status
        self._docker_label = ctk.CTkLabel(self, text="Checking Docker...", text_color="gray")
        self._docker_label.pack(pady=(15, 5))

        # Docker error (shown when Docker unavailable)
        self._docker_error = ctk.CTkLabel(
            self,
            text="Docker Desktop is required. Please install and start Docker Desktop.",
            font=ctk.CTkFont(size=12),
            text_color="red",
            wraplength=400,
        )
        self._docker_link = ctk.CTkLabel(
            self,
            text="https://www.docker.com/products/docker-desktop/",
            font=ctk.CTkFont(size=11),
            text_color="blue",
            cursor="hand2",
        )

        # Start button
        self._start_btn = ctk.CTkButton(
            self,
            text="Start",
            command=self._on_start,
            width=120,
            height=36,
            state="disabled",
        )
        self._start_btn.pack(pady=20)

        # Status message
        self._status = ctk.CTkLabel(self, text="", text_color="gray", wraplength=400)
        self._status.pack(pady=(5, 0))

        # Check Docker on load
        self.after(100, self._check_docker)

    def _check_docker(self):
        """Check if Docker is available (run in thread to avoid blocking UI)."""
        def _do_check():
            try:
                from worker.docker_manager import DockerManager

                # Match worker's Docker socket logic
                docker_socket = None
                if os.getenv("GRIDX_DOCKER_SOCKET"):
                    docker_socket = os.getenv("GRIDX_DOCKER_SOCKET")
                elif os.getenv("DOCKER_HOST"):
                    docker_socket = os.getenv("DOCKER_HOST")
                elif os.name == "nt":
                    docker_socket = "npipe:////./pipe/docker_engine"

                mgr = DockerManager(docker_socket=docker_socket)
                available = mgr.available
                self.after(0, lambda: self._on_docker_result(available))
            except Exception as e:
                self.after(0, lambda: self._on_docker_result(False, str(e)))

        t = threading.Thread(target=_do_check, daemon=True)
        t.start()

    def _on_docker_result(self, available: bool, error: Optional[str] = None):
        """Handle Docker check result on main thread."""
        if available:
            self._docker_label.configure(text="Docker: Available", text_color="green")
            self._start_btn.configure(state="normal")
            self._docker_error.pack_forget()
            self._docker_link.pack_forget()
        else:
            self._docker_label.configure(text="Docker: Not available", text_color="red")
            self._docker_error.pack(pady=(5, 2))
            self._docker_link.pack(pady=(0, 10))
            self._docker_link.bind("<Button-1>", lambda e: self._open_docker_url())
            self._start_btn.configure(state="disabled")

    def _open_docker_url(self):
        """Open Docker Desktop download URL in browser."""
        import webbrowser
        webbrowser.open("https://www.docker.com/products/docker-desktop/")

    def _on_start(self):
        """Start the worker and switch to dashboard."""
        username = self._username.get().strip()
        password = self._password.get().strip()
        coordinator_ip = self._coordinator_ip.get().strip() or "localhost"

        if not username:
            self._status.configure(text="Please enter a username.", text_color="orange")
            return
        if not password:
            self._status.configure(text="Please enter a password.", text_color="orange")
            return

        self._start_btn.configure(state="disabled", text="Starting...")
        self._status.configure(text="Connecting...", text_color="gray")

        def _run_worker():
            try:
                from worker.main import HybridWorker

                worker = HybridWorker(
                    user_id=username,
                    password=password,
                    coordinator_ip=coordinator_ip,
                    http_port=8081,
                    ws_port=8080,
                )

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _run():
                    await worker.run_worker()

                task = loop.create_task(_run())

                def _run_loop():
                    try:
                        loop.run_forever()
                    except Exception:
                        pass
                    finally:
                        loop.close()

                self.loop = loop
                self.worker = worker
                self.worker_task = task
                self._thread = threading.Thread(target=_run_loop, daemon=True)
                self._thread.start()

                # Give worker time to complete handshake (auth may fail quickly)
                self._check_after_id = self.after(5000, self._check_and_switch)

            except Exception as e:
                self.after(0, lambda: self._on_start_error(str(e)))

        t = threading.Thread(target=_run_worker, daemon=True)
        t.start()

    def _check_and_switch(self):
        """Check auth status and switch to dashboard or show error."""
        self._check_after_id = None
        if self.worker_task and self.worker_task.done():
            try:
                self.worker_task.result()
            except RuntimeError as e:
                if "Authentication failed" in str(e):
                    self._start_btn.configure(state="normal", text="Start")
                    self._status.configure(
                        text="Authentication failed. Check username and password.",
                        text_color="red",
                    )
                    return
                raise
            except Exception as e:
                self._start_btn.configure(state="normal", text="Start")
                self._status.configure(text=f"Error: {e}", text_color="red")
                return

        # Success - switch to dashboard
        self._start_btn.configure(state="normal", text="Start")
        self._status.configure(text="")
        if self.on_success:
            self.on_success()

    def _on_start_error(self, msg: str):
        """Handle start error on main thread."""
        self._start_btn.configure(state="normal", text="Start")
        self._status.configure(text=f"Error: {msg}", text_color="red")
