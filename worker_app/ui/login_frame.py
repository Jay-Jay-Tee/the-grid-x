"""
Login screen - username, password, coordinator settings, Docker check.
90s hacking terminal aesthetic.
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

from .theme import (
    BG_DARK, BG_PANEL, GREEN, GREEN_DIM, GREEN_BRIGHT, AMBER, RED, GRAY,
    TERMINAL_FONT, TERMINAL_FONT_SMALL, TERMINAL_FONT_TITLE,
)


class LoginFrame(ctk.CTkFrame):
    """Login form - terminal style."""

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
        """Build the login form UI - 90s terminal style."""
        # ASCII art header
        header = ctk.CTkLabel(
            self,
            text="╔══════════════════════════════════════╗\n"
                 "║   G R I D - X   W O R K E R   N O D E   ║\n"
                 "║      [ ACCESS TERMINAL v1.0 ]         ║\n"
                 "╚══════════════════════════════════════╝",
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color=GREEN,
        )
        header.pack(pady=(0, 24))

        # Username
        ctk.CTkLabel(self, text="> USER_ID:", font=TERMINAL_FONT, text_color=GREEN_DIM).pack(anchor="w", pady=(8, 0))
        self._username = ctk.CTkEntry(
            self, placeholder_text="enter_handle", width=340,
            font=TERMINAL_FONT, fg_color=BG_PANEL, border_color=GREEN_DIM,
            text_color=GREEN, placeholder_text_color=GRAY,
        )
        self._username.pack(pady=(2, 10), fill="x")

        # Password
        ctk.CTkLabel(self, text="> PASSWORD:", font=TERMINAL_FONT, text_color=GREEN_DIM).pack(anchor="w", pady=(8, 0))
        self._password = ctk.CTkEntry(
            self, placeholder_text="••••••••", show="•", width=340,
            font=TERMINAL_FONT, fg_color=BG_PANEL, border_color=GREEN_DIM,
            text_color=GREEN,
        )
        self._password.pack(pady=(2, 10), fill="x")

        # Coordinator
        ctk.CTkLabel(self, text="> COORDINATOR_URL:", font=TERMINAL_FONT, text_color=GREEN_DIM).pack(anchor="w", pady=(8, 0))
        self._coordinator_ip = ctk.CTkEntry(
            self, placeholder_text="https://your-coordinator.up.railway.app", width=340,
            font=TERMINAL_FONT_SMALL, fg_color=BG_PANEL, border_color=GREEN_DIM,
            text_color=GREEN, placeholder_text_color=GRAY,
        )
        self._coordinator_ip.insert(0, "localhost")
        self._coordinator_ip.pack(pady=(2, 10), fill="x")

        # Docker status
        self._docker_label = ctk.CTkLabel(
            self, text="[ * ] Checking Docker daemon...",
            font=TERMINAL_FONT_SMALL, text_color=AMBER,
        )
        self._docker_label.pack(pady=(18, 5))

        self._docker_error = ctk.CTkLabel(
            self, text="[ ! ] Docker Desktop required. Install and start Docker.",
            font=TERMINAL_FONT_SMALL, text_color=RED, wraplength=400,
        )
        self._docker_link = ctk.CTkLabel(
            self, text="  >> https://www.docker.com/products/docker-desktop/",
            font=TERMINAL_FONT_SMALL, text_color=GREEN_BRIGHT, cursor="hand2",
        )

        # Start button - terminal style
        self._start_btn = ctk.CTkButton(
            self, text="[ INITIATE CONNECTION ]",
            command=self._on_start, width=260, height=36,
            font=TERMINAL_FONT, state="disabled",
            fg_color=BG_PANEL, text_color=GREEN, border_width=1, border_color=GREEN_DIM,
            hover_color=GREEN_DIM, hover=True,
        )
        self._start_btn.pack(pady=24)

        self._status = ctk.CTkLabel(
            self, text="", font=TERMINAL_FONT_SMALL,
            text_color=AMBER, wraplength=420,
        )
        self._status.pack(pady=(5, 0))

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
            self._docker_label.configure(text="[ OK ] Docker daemon online", text_color=GREEN)
            self._start_btn.configure(state="normal")
            self._docker_error.pack_forget()
            self._docker_link.pack_forget()
        else:
            self._docker_label.configure(text="[ FAIL ] Docker daemon offline", text_color=RED)
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
            self._status.configure(text="[ ! ] USER_ID required", text_color=AMBER)
            return
        if not password:
            self._status.configure(text="[ ! ] PASSWORD required", text_color=AMBER)
            return

        self._start_btn.configure(state="disabled", text="[ CONNECTING... ]")
        self._status.configure(text="[ * ] Establishing secure link...", text_color=GREEN_DIM)

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
                    self._start_btn.configure(state="normal", text="[ INITIATE CONNECTION ]")
                    self._status.configure(
                        text="[ ACCESS DENIED ] Invalid credentials.",
                        text_color=RED,
                    )
                    return
                raise
            except Exception as e:
                self._start_btn.configure(state="normal", text="[ INITIATE CONNECTION ]")
                self._status.configure(text=f"[ ERROR ] {e}", text_color=RED)
                return

        # Success - switch to dashboard
        self._start_btn.configure(state="normal", text="[ INITIATE CONNECTION ]")
        self._status.configure(text="")
        if self.on_success:
            self.on_success()

    def _on_start_error(self, msg: str):
        """Handle start error on main thread."""
        self._start_btn.configure(state="normal", text="[ INITIATE CONNECTION ]")
        self._status.configure(text=f"[ ERROR ] {msg}", text_color=RED)
