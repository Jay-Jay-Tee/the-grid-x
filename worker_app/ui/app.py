"""
Main application window - frame switching between login and dashboard.
90s hacking terminal aesthetic.
"""

import customtkinter as ctk
from .login_frame import LoginFrame
from .dashboard_frame import DashboardFrame
from .theme import BG_DARK


class GridXApp(ctk.CTk):
    """Main Grid-X Worker application window."""

    def __init__(self):
        super().__init__()
        self.title("GRID-X // WORKER_NODE v1.0")
        self.geometry("750x700")
        self.minsize(550, 550)

        # Terminal-style window - black bg
        self.configure(fg_color=BG_DARK)
        self._set_terminal_titlebar()

        # Handle window close (X button) for proper cleanup
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        # Container for frames
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=16, pady=16)

        self._current_frame = None
        self._login_frame = None
        self._dashboard_frame = None

        self._show_login()

    def _show_login(self):
        """Show login screen."""
        if self._current_frame:
            self._current_frame.destroy()
        self._login_frame = LoginFrame(self._container, on_success=self._on_login_success)
        self._login_frame.pack(fill="both", expand=True)
        self._current_frame = self._login_frame

    def _on_login_success(self):
        """Called when login succeeds - switch to dashboard."""
        if self._current_frame:
            self._current_frame.destroy()
        self._dashboard_frame = DashboardFrame(
            self._container,
            worker=self._login_frame.worker,
            worker_task=self._login_frame.worker_task,
            loop=self._login_frame.loop,
            on_quit=self._on_quit,
        )
        self._dashboard_frame.pack(fill="both", expand=True)
        self._current_frame = self._dashboard_frame

    def _handle_close(self):
        """Handle window close (X button) - ensures worker cleanup when on dashboard."""
        if self._current_frame and hasattr(self._current_frame, "_on_quit"):
            self._current_frame._on_quit()
        else:
            self.quit()

    def _set_terminal_titlebar(self):
        """Attempt to style title bar (platform-dependent)."""
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass

    def _on_quit(self):
        """Called when user quits from dashboard."""
        self.quit()
