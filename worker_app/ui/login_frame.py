"""
Login screen - username, password, coordinator settings, Docker check.
Enhanced 90s hacking terminal aesthetic with animations and CRT effects.
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
    BG_DARK, BG_PANEL, BG_DARKEST, GREEN, GREEN_DIM, GREEN_BRIGHT, GREEN_GLOW,
    AMBER, CYAN, MAGENTA, RED, RED_BRIGHT, GRAY, GRAY_DARK, GRAY_LIGHT,
    TERMINAL_FONT, TERMINAL_FONT_SMALL, TERMINAL_FONT_TITLE, TERMINAL_FONT_MEGA,
    ANIM_CURSOR_BLINK, ANIM_PULSE_FAST,
)


class LoginFrame(ctk.CTkFrame):
    """Login form - enhanced terminal style with animations."""

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
        
        # Animation state
        self._anim_running = True
        self._scan_line_y = 0
        self._title_blink = True
        self._border_pulse = 0

        self._build_ui()
        self._start_animations()

    def _build_ui(self):
        """Build the login form UI - Enhanced 90s terminal style."""
        
        # Animated title frame with border
        title_container = ctk.CTkFrame(
            self, fg_color=BG_DARKEST, corner_radius=0,
            border_width=2, border_color=GREEN_DIM
        )
        title_container.pack(pady=(0, 24), padx=20, fill="x")
        
        # ASCII art header with glow effect
        self._header = ctk.CTkLabel(
            title_container,
            text="╔═══════════════════════════════════════╗\n"
                 "║  G R I D - X   W O R K E R   N O D E  ║\n"
                 "║     [ ACCESS TERMINAL v1.0 ]          ║\n"
                 "╚═══════════════════════════════════════╝",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=GREEN_BRIGHT,
        )
        self._header.pack(pady=16, padx=10)
        
        # Blinking cursor indicator
        self._cursor_label = ctk.CTkLabel(
            title_container,
            text="█ INITIALIZING SECURE CONNECTION...",
            font=TERMINAL_FONT_SMALL,
            text_color=CYAN,
        )
        self._cursor_label.pack(pady=(0, 12))

        # Main form container with scan line effect
        form_frame = ctk.CTkFrame(
            self, fg_color=BG_PANEL, corner_radius=0,
            border_width=1, border_color=GREEN_DIM
        )
        form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        inner_form = ctk.CTkFrame(form_frame, fg_color="transparent")
        inner_form.pack(padx=20, pady=20, fill="both", expand=True)

        # Username with animated label
        user_label_frame = ctk.CTkFrame(inner_form, fg_color="transparent")
        user_label_frame.pack(anchor="w", pady=(8, 0), fill="x")
        
        ctk.CTkLabel(
            user_label_frame, text="►", 
            font=TERMINAL_FONT, text_color=GREEN_BRIGHT
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(
            user_label_frame, text="USER_ID:", 
            font=TERMINAL_FONT, text_color=GREEN_DIM
        ).pack(side="left")
        
        self._username = ctk.CTkEntry(
            inner_form, placeholder_text="enter_handle", width=340,
            font=TERMINAL_FONT, fg_color=BG_DARKEST, 
            border_color=GREEN_DIM, border_width=2,
            text_color=GREEN_BRIGHT, placeholder_text_color=GRAY,
        )
        self._username.pack(pady=(4, 12), fill="x")

        # Password with animated label
        pass_label_frame = ctk.CTkFrame(inner_form, fg_color="transparent")
        pass_label_frame.pack(anchor="w", pady=(8, 0), fill="x")
        
        ctk.CTkLabel(
            pass_label_frame, text="►", 
            font=TERMINAL_FONT, text_color=GREEN_BRIGHT
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(
            pass_label_frame, text="PASSWORD:", 
            font=TERMINAL_FONT, text_color=GREEN_DIM
        ).pack(side="left")
        
        self._password = ctk.CTkEntry(
            inner_form, placeholder_text="••••••••", show="•", width=340,
            font=TERMINAL_FONT, fg_color=BG_DARKEST, 
            border_color=GREEN_DIM, border_width=2,
            text_color=GREEN_BRIGHT,
        )
        self._password.pack(pady=(4, 12), fill="x")

        # Coordinator with animated label
        coord_label_frame = ctk.CTkFrame(inner_form, fg_color="transparent")
        coord_label_frame.pack(anchor="w", pady=(8, 0), fill="x")
        
        ctk.CTkLabel(
            coord_label_frame, text="►", 
            font=TERMINAL_FONT, text_color=GREEN_BRIGHT
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(
            coord_label_frame, text="COORDINATOR_URL:", 
            font=TERMINAL_FONT, text_color=GREEN_DIM
        ).pack(side="left")
        
        self._coordinator_ip = ctk.CTkEntry(
            inner_form, placeholder_text="https://your-coordinator.example.com",
            width=340,
            font=TERMINAL_FONT_SMALL, fg_color=BG_DARKEST,
            border_color=GREEN_DIM, border_width=2,
            text_color=GREEN, placeholder_text_color=GRAY,
        )
        self._coordinator_ip.insert(0, "localhost")
        self._coordinator_ip.pack(pady=(4, 10), fill="x")

        # Docker status with pulsing indicator
        docker_container = ctk.CTkFrame(
            inner_form, fg_color=BG_DARKEST, corner_radius=4,
            border_width=1, border_color=GRAY_DARK
        )
        docker_container.pack(pady=(18, 5), fill="x")
        
        self._docker_label = ctk.CTkLabel(
            docker_container, text="[ ◉ ] Checking Docker daemon...",
            font=TERMINAL_FONT_SMALL, text_color=AMBER,
        )
        self._docker_label.pack(pady=10, padx=12)

        self._docker_error = ctk.CTkLabel(
            inner_form, text="[ ⚠ ] Docker Desktop required. Install and start Docker.",
            font=TERMINAL_FONT_SMALL, text_color=RED_BRIGHT, wraplength=400,
        )
        
        link_frame = ctk.CTkFrame(inner_form, fg_color="transparent")
        
        ctk.CTkLabel(
            link_frame, text="  ►► ", 
            font=TERMINAL_FONT_SMALL, text_color=CYAN
        ).pack(side="left")
        
        self._docker_link = ctk.CTkLabel(
            link_frame, text="https://www.docker.com/products/docker-desktop/",
            font=TERMINAL_FONT_SMALL, text_color=CYAN, cursor="hand2",
        )
        self._docker_link.pack(side="left")
        
        self._docker_link_frame = link_frame

        # Start button with glow effect
        button_container = ctk.CTkFrame(self, fg_color="transparent")
        button_container.pack(pady=24)
        
        self._start_btn = ctk.CTkButton(
            button_container, text="[ ▶ INITIATE CONNECTION ]",
            command=self._on_start, width=280, height=40,
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            state="disabled",
            fg_color=BG_PANEL, text_color=GREEN_BRIGHT, 
            border_width=2, border_color=GREEN_DIM,
            hover_color=GREEN_DIM, hover=True,
            corner_radius=0,
        )
        self._start_btn.pack()

        # Status message
        self._status = ctk.CTkLabel(
            self, text="", font=TERMINAL_FONT_SMALL,
            text_color=AMBER, wraplength=420,
        )
        self._status.pack(pady=(5, 0))
        
        # Footer decoration
        footer_frame = ctk.CTkFrame(
            self, fg_color="transparent", height=30
        )
        footer_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        self._footer_label = ctk.CTkLabel(
            footer_frame,
            text="═══════════════════════════════════════════════════════",
            font=TERMINAL_FONT_SMALL,
            text_color=GREEN_DIM,
        )
        self._footer_label.pack()

        self.after(100, self._check_docker)

    def _start_animations(self):
        """Start all UI animations."""
        self._animate_title_blink()
        self._animate_border_pulse()

    def _animate_title_blink(self):
        """Blink the cursor in the title."""
        if not self._anim_running:
            return
        
        if self._title_blink:
            text = "█ INITIALIZING SECURE CONNECTION..."
        else:
            text = "  INITIALIZING SECURE CONNECTION..."
        
        self._cursor_label.configure(text=text)
        self._title_blink = not self._title_blink
        self.after(ANIM_CURSOR_BLINK, self._animate_title_blink)

    def _animate_border_pulse(self):
        """Pulse the main border color."""
        if not self._anim_running:
            return
        
        self._border_pulse = (self._border_pulse + 1) % 3
        colors = [GREEN_DIM, GREEN, GREEN_BRIGHT]
        
        try:
            self._header.configure(text_color=colors[self._border_pulse])
        except:
            pass
        
        self.after(ANIM_PULSE_FAST, self._animate_border_pulse)

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
            self._docker_label.configure(
                text="[ ✓ ] Docker daemon ONLINE", 
                text_color=GREEN_BRIGHT
            )
            self._start_btn.configure(state="normal")
            self._docker_error.pack_forget()
            self._docker_link_frame.pack_forget()
            self._cursor_label.configure(
                text="█ READY TO CONNECT",
                text_color=GREEN_BRIGHT
            )
        else:
            self._docker_label.configure(
                text="[ ✗ ] Docker daemon OFFLINE", 
                text_color=RED_BRIGHT
            )
            self._docker_error.pack(pady=(5, 2))
            self._docker_link_frame.pack(pady=(0, 10))
            self._docker_link.bind("<Button-1>", lambda e: self._open_docker_url())
            self._start_btn.configure(state="disabled")
            self._cursor_label.configure(
                text="█ DOCKER REQUIRED",
                text_color=RED
            )

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
            self._status.configure(text="[ ⚠ ] USER_ID required", text_color=AMBER)
            return
        if not password:
            self._status.configure(text="[ ⚠ ] PASSWORD required", text_color=AMBER)
            return

        self._start_btn.configure(
            state="disabled", 
            text="[ ◉ CONNECTING... ]",
            border_color=AMBER
        )
        self._status.configure(
            text="[ ◉ ] Establishing secure link...", 
            text_color=CYAN
        )
        self._cursor_label.configure(
            text="█ HANDSHAKE IN PROGRESS...",
            text_color=AMBER
        )

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
                    self._start_btn.configure(
                        state="normal", 
                        text="[ ▶ INITIATE CONNECTION ]",
                        border_color=GREEN_DIM
                    )
                    self._status.configure(
                        text="[ ✗ ACCESS DENIED ] Invalid credentials.",
                        text_color=RED_BRIGHT,
                    )
                    self._cursor_label.configure(
                        text="█ AUTHENTICATION FAILED",
                        text_color=RED
                    )
                    return
                raise
            except Exception as e:
                self._start_btn.configure(
                    state="normal", 
                    text="[ ▶ INITIATE CONNECTION ]",
                    border_color=GREEN_DIM
                )
                self._status.configure(text=f"[ ✗ ERROR ] {e}", text_color=RED_BRIGHT)
                self._cursor_label.configure(
                    text="█ CONNECTION FAILED",
                    text_color=RED
                )
                return

        # Success - switch to dashboard
        self._anim_running = False
        self._start_btn.configure(
            state="normal", 
            text="[ ▶ INITIATE CONNECTION ]",
            border_color=GREEN_DIM
        )
        self._status.configure(text="")
        if self.on_success:
            self.on_success()

    def _on_start_error(self, msg: str):
        """Handle start error on main thread."""
        self._start_btn.configure(
            state="normal", 
            text="[ ▶ INITIATE CONNECTION ]",
            border_color=GREEN_DIM
        )
        self._status.configure(text=f"[ ✗ ERROR ] {msg}", text_color=RED_BRIGHT)
        self._cursor_label.configure(
            text="█ SYSTEM ERROR",
            text_color=RED
        )

    def destroy(self):
        """Clean up animations before destroying."""
        self._anim_running = False
        super().destroy()
