"""
Shared state between UI and worker.
Thread-safe state holder with optional callbacks for UI updates.
"""

import threading
from typing import Optional, Callable, List, Any, Dict


class AppState:
    """Shared application state between worker thread and UI."""

    def __init__(self):
        self._lock = threading.Lock()
        self._worker = None
        self._worker_task = None
        self._loop = None
        self._on_status_change: Optional[Callable[[], None]] = None

    def set_worker(self, worker):
        """Set the HybridWorker instance."""
        with self._lock:
            self._worker = worker

    def get_worker(self):
        """Get the HybridWorker instance."""
        with self._lock:
            return self._worker

    def set_worker_task(self, task):
        """Set the asyncio task running the worker."""
        with self._lock:
            self._worker_task = task

    def get_worker_task(self):
        """Get the asyncio task running the worker."""
        with self._lock:
            return self._worker_task

    def set_loop(self, loop):
        """Set the asyncio event loop."""
        with self._lock:
            self._loop = loop

    def get_loop(self):
        """Get the asyncio event loop."""
        with self._lock:
            return self._loop

    def set_on_status_change(self, callback: Optional[Callable[[], None]]):
        """Set callback invoked when status may have changed (for UI refresh)."""
        with self._lock:
            self._on_status_change = callback

    def notify_status_change(self):
        """Notify that status may have changed."""
        with self._lock:
            cb = self._on_status_change
        if cb:
            try:
                cb()
            except Exception:
                pass

    def is_connected(self) -> bool:
        """Whether worker is connected to coordinator."""
        w = self.get_worker()
        return w.is_connected if w else False

    def is_paused(self) -> bool:
        """Whether worker is paused."""
        w = self.get_worker()
        return w.is_paused() if w else False

    def get_credits(self) -> Optional[float]:
        """Get credit balance from coordinator."""
        w = self.get_worker()
        return w.get_credits() if w else None

    def get_recent_activity(self, count: int = 15) -> List[Dict[str, Any]]:
        """Get recent activity log entries."""
        w = self.get_worker()
        if not w or not w.activity_log:
            return []
        return w.activity_log.get_recent(count)
