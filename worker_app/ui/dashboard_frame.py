"""
Dashboard - connection status, credits, pause/resume toggle, activity log,
job submission (code/file, language), and recent jobs with output viewer.
"""

import os
import threading
from tkinter import filedialog
from typing import Optional, Callable, Any, List, Dict

import customtkinter as ctk

# Supported languages (coordinator may restrict to python)
LANGUAGES = [
    ("Python", "python"),
    ("JavaScript", "javascript"),
    ("Node.js", "node"),
    ("Bash", "bash"),
]


class DashboardFrame(ctk.CTkFrame):
    """Main dashboard with status, credits, pause toggle, activity log, job submission, and recent jobs."""

    def __init__(
        self,
        parent,
        worker,
        worker_task,
        loop,
        on_quit: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.worker = worker
        self.worker_task = worker_task
        self.loop = loop
        self.on_quit = on_quit
        self._refresh_job = None
        self._shutting_down = False

        self._build_ui()
        self._start_refresh()

    def _build_ui(self):
        """Build the dashboard UI with tabs."""
        # Title
        title = ctk.CTkLabel(
            self,
            text=f"Grid-X Worker : {self.worker.user_id}",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.pack(pady=(0, 10))

        # Tabs
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, pady=(0, 10))

        self._tab_status = self._tabview.add("Status")
        self._tab_submit = self._tabview.add("Submit Job")
        self._tab_jobs = self._tabview.add("Recent Jobs")

        self._build_status_tab()
        self._build_submit_tab()
        self._build_jobs_tab()

        # Quit button
        ctk.CTkButton(self, text="Quit", command=self._on_quit, width=100, height=32).pack(pady=(10, 0))

    def _build_status_tab(self):
        """Status tab: connection, credits, pause, activity."""
        # Connection status
        status_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        status_frame.pack(fill="x", pady=(0, 10))

        self._status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray",
        )
        self._status_indicator.pack(side="left", padx=(0, 8))
        self._status_text = ctk.CTkLabel(status_frame, text="Checking...", font=ctk.CTkFont(size=14))
        self._status_text.pack(side="left")

        # Credits
        credits_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        credits_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(credits_frame, text="Credits: ", font=ctk.CTkFont(size=14)).pack(side="left")
        self._credits_label = ctk.CTkLabel(credits_frame, text="NULL", font=ctk.CTkFont(size=14, weight="bold"))
        self._credits_label.pack(side="left")
        self._refresh_credits_btn = ctk.CTkButton(
            credits_frame,
            text="Refresh",
            width=70,
            height=24,
            command=self._refresh_credits,
        )
        self._refresh_credits_btn.pack(side="left", padx=(10, 0))

        # Pause / Resume
        toggle_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(10, 15))

        self._pause_btn = ctk.CTkButton(
            toggle_frame,
            text="Pause",
            command=self._on_pause_toggle,
            width=120,
            height=36,
            fg_color="#c75c5c",
            hover_color="#a04a4a",
        )
        self._pause_btn.pack(side="left", padx=(0, 8))

        self._resume_btn = ctk.CTkButton(
            toggle_frame,
            text="Resume",
            command=self._on_pause_toggle,
            width=120,
            height=36,
            state="disabled",
        )
        self._resume_btn.pack(side="left")

        # Activity log
        ctk.CTkLabel(self._tab_status, text="Recent Activity", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5)
        )
        self._activity_text = ctk.CTkTextbox(self._tab_status, height=200, state="disabled", wrap="word")
        self._activity_text.pack(fill="both", expand=True, pady=(0, 10))

    def _build_submit_tab(self):
        """Submit job tab: code input, file load, language, submit."""
        ctk.CTkLabel(self._tab_submit, text="Code", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
        self._code_text = ctk.CTkTextbox(self._tab_submit, height=120, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self._code_text.pack(fill="x", pady=(0, 10))
        self._code_text.insert("1.0", "# Enter your code here\nprint('Hello from Grid-X!')")

        btn_row = ctk.CTkFrame(self._tab_submit, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(btn_row, text="Load from file", width=120, command=self._load_code_from_file).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(btn_row, text="Language:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(10, 5))
        self._language_var = ctk.StringVar(value="Python")
        self._language_menu = ctk.CTkOptionMenu(
            btn_row,
            values=[label for label, _ in LANGUAGES],
            variable=self._language_var,
            width=120,
        )
        self._language_menu.pack(side="left", padx=(0, 10))

        self._submit_btn = ctk.CTkButton(
            btn_row,
            text="Submit Job",
            width=120,
            height=32,
            command=self._on_submit_job,
        )
        self._submit_btn.pack(side="left")

        self._submit_status = ctk.CTkLabel(self._tab_submit, text="", text_color="gray", wraplength=400)
        self._submit_status.pack(anchor="w", pady=(5, 0))

        # Results output area - shows stdout/stderr of submitted job
        ctk.CTkLabel(self._tab_submit, text="Results", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5)
        )
        self._submit_output = ctk.CTkTextbox(
            self._tab_submit, height=150, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=12)
        )
        self._submit_output.pack(fill="both", expand=True, pady=(0, 10))
        self._show_submit_output("Submit code to see results here.")

    def _get_language_value(self) -> str:
        """Map displayed language name to API value."""
        choice = self._language_var.get()
        for label, val in LANGUAGES:
            if label == choice:
                return val
        return "python"

    def _load_code_from_file(self):
        """Load code from a file into the text area."""
        path = filedialog.askopenfilename(
            title="Select code file",
            filetypes=[
                ("Python", "*.py"),
                ("JavaScript", "*.js"),
                ("All text", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    code = f.read()
                self._code_text.delete("1.0", "end")
                self._code_text.insert("1.0", code)
                # Infer language from extension
                ext = os.path.splitext(path)[1].lower()
                if ext == ".py":
                    self._language_var.set("Python")
                elif ext in (".js", ".mjs"):
                    self._language_var.set("JavaScript")
                elif ext == ".sh":
                    self._language_var.set("Bash")
                self._submit_status.configure(text=f"Loaded: {os.path.basename(path)}", text_color="gray")
            except Exception as e:
                self._submit_status.configure(text=f"Error: {e}", text_color="red")

    def _on_submit_job(self):
        """Submit the code as a job."""
        code = self._code_text.get("1.0", "end").strip()
        if not code:
            self._submit_status.configure(text="Please enter some code.", text_color="orange")
            return

        lang_val = self._get_language_value()

        if not self.worker.is_connected:
            self._submit_status.configure(text="Not connected. Connect first to submit jobs.", text_color="red")
            return

        self._submit_btn.configure(state="disabled")
        self._submit_status.configure(text="Submitting...", text_color="gray")
        self._show_submit_output("Waiting...")

        def _do_submit():
            try:
                job_id = self.worker.submit_job(code, language=lang_val, wait_for_result=False)
                if job_id:
                    from worker_app.job_history import add_job_to_history
                    add_job_to_history(self.worker.user_id, job_id, lang_val, code[:80])
                    def _ok():
                        self._submit_status.configure(text=f"Submitted. Waiting for result...", text_color="green")
                        self._submit_btn.configure(state="normal")
                    self.after(0, _ok)
                    self._poll_job_and_show_result(job_id)
                else:
                    def _fail():
                        self._submit_status.configure(text="Submit failed. Check connection and credits.", text_color="red")
                        self._submit_btn.configure(state="normal")
                        self._show_submit_output("Submit failed.")
                    self.after(0, _fail)
            except Exception as e:
                def _err():
                    self._submit_status.configure(text=f"Error: {e}", text_color="red")
                    self._submit_btn.configure(state="normal")
                    self._show_submit_output(f"Error: {e}")
                self.after(0, _err)

        threading.Thread(target=_do_submit, daemon=True).start()

    def _show_submit_output(self, text: str):
        """Display text in the Submit Job results area."""
        self._submit_output.configure(state="normal")
        self._submit_output.delete("1.0", "end")
        self._submit_output.insert("1.0", text)
        self._submit_output.configure(state="disabled")

    def _poll_job_and_show_result(self, job_id: str):
        """Poll job status until complete, then display result in Submit Job tab."""
        def _poll():
            import time
            max_wait = 300
            start = time.time()
            while time.time() - start < max_wait:
                job = self.worker.get_job(job_id) if self.worker.is_connected else None
                if job:
                    from worker_app.job_history import update_job_in_history
                    update_job_in_history(self.worker.user_id, job)
                    status = job.get("status", "")
                    if status in ("completed", "failed", "error"):
                        def _display():
                            self._display_job_output_in_submit(job)
                        self.after(0, _display)
                        return
                time.sleep(1.5)
            def _timeout():
                self._show_submit_output(f"Job {job_id[:12]}...\n\nTimeout waiting for result.")
            self.after(0, _timeout)

        threading.Thread(target=_poll, daemon=True).start()

    def _display_job_output_in_submit(self, job: Dict[str, Any]):
        """Display job output in the Submit Job results area."""
        stdout = job.get("stdout", "")
        stderr = job.get("stderr", "")
        exit_code = job.get("exit_code")
        status = job.get("status", "?")
        parts = [f"Status: {status}"]
        if exit_code is not None:
            parts.append(f"Exit code: {exit_code}")
        parts.extend([
            "",
            "=== stdout ===",
            stdout or "(empty)",
            "",
            "=== stderr ===",
            stderr or "(empty)",
        ])
        text = "\n".join(parts)
        self._show_submit_output(text)

    def _build_jobs_tab(self):
        """Recent jobs tab: list + output viewer."""
        top_row = ctk.CTkFrame(self._tab_jobs, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(top_row, text="Recent Jobs", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(top_row, text="Refresh", width=80, command=self._update_jobs_list).pack(side="right")

        # Jobs list (scrollable)
        self._jobs_frame = ctk.CTkScrollableFrame(self._tab_jobs, height=120)
        self._jobs_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self._tab_jobs, text="Output (click a job)", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(5, 5)
        )
        self._output_text = ctk.CTkTextbox(self._tab_jobs, height=150, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self._output_text.pack(fill="both", expand=True, pady=(0, 10))

    def _update_jobs_list(self):
        """Refresh the recent jobs list."""
        def _fetch():
            try:
                from worker_app.job_history import get_merged_job_history
                coord_jobs = []
                if self.worker.is_connected:
                    coord_jobs = self.worker.list_jobs(limit=50)
                merged = get_merged_job_history(self.worker.user_id, coord_jobs)
                self.after(0, lambda: self._render_jobs_list(merged))
            except Exception:
                self.after(0, lambda: self._render_jobs_list([]))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_jobs_list(self, jobs: List[Dict[str, Any]]):
        """Render job list into the scrollable frame."""
        for w in self._jobs_frame.winfo_children():
            w.destroy()

        if not jobs:
            ctk.CTkLabel(self._jobs_frame, text="No jobs yet. Submit code in the Submit Job tab.", text_color="gray").pack(anchor="w")
            return

        for j in jobs[:30]:
            job_id = j.get("job_id") or j.get("id", "?")
            status = j.get("status", "?")
            lang = j.get("language", "python")
            row = ctk.CTkFrame(self._jobs_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            color = "green" if status == "completed" else ("red" if status in ("failed", "error") else "gray")
            lbl = ctk.CTkLabel(
                row,
                text=f"{job_id[:12]}... | {status} | {lang}",
                font=ctk.CTkFont(size=12),
                text_color=color,
                cursor="hand2",
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, jid=job_id: self._show_job_output(jid))
            row.bind("<Button-1>", lambda e, jid=job_id: self._show_job_output(jid))

    def _show_job_output(self, job_id: str):
        """Show output for a job (from local cache or fetch from coordinator)."""
        def _fetch():
            job = None
            if self.worker.is_connected:
                job = self.worker.get_job(job_id)
                if job:
                    from worker_app.job_history import update_job_in_history
                    update_job_in_history(self.worker.user_id, job)
            if not job:
                from worker_app.job_history import load_job_history
                local = load_job_history(self.worker.user_id)
                for j in local:
                    if (j.get("job_id") or j.get("id")) == job_id:
                        job = j
                        break
            def _show():
                self._display_job_output(job_id, job)
            self.after(0, _show)

        threading.Thread(target=_fetch, daemon=True).start()

    def _display_job_output(self, job_id: str, job: Optional[Dict]):
        """Display job output in the output text area."""
        self._output_text.configure(state="normal")
        self._output_text.delete("1.0", "end")
        if not job:
            self._output_text.insert("1.0", f"Job {job_id}\n\nNot found. If disconnected, only cached jobs are shown.")
        else:
            status = job.get("status", "?")
            stdout = job.get("stdout", "")
            stderr = job.get("stderr", "")
            exit_code = job.get("exit_code")
            lines = [
                f"Job: {job_id}",
                f"Status: {status}",
                f"Language: {job.get('language', 'python')}",
                "",
                "=== stdout ===",
                stdout or "(empty)",
                "",
                "=== stderr ===",
                stderr or "(empty)",
            ]
            if exit_code is not None:
                lines.insert(3, f"Exit code: {exit_code}")
            self._output_text.insert("1.0", "\n".join(lines))
        self._output_text.configure(state="disabled")

    def _start_refresh(self):
        """Start periodic UI refresh."""
        self._do_refresh()

    def _do_refresh(self):
        """Periodic refresh: only status, activity, pause buttons (local state). Credits and jobs only on manual Refresh."""
        self._update_status()
        self._update_activity()
        self._update_pause_buttons()
        self._refresh_job = self.after(2000, self._do_refresh)

    def _update_status(self):
        """Update connection status display."""
        if self.worker.is_connected:
            self._status_indicator.configure(text_color="green")
            self._status_text.configure(text="Connected")
        elif self.worker.is_paused():
            self._status_indicator.configure(text_color="orange")
            self._status_text.configure(text="Paused")
        else:
            self._status_indicator.configure(text_color="red")
            self._status_text.configure(text="Disconnected")

    def _update_credits(self):
        """Update credits display (fetch in thread to avoid blocking)."""
        def _fetch():
            bal = self.worker.get_credits()
            def _set():
                if bal is not None:
                    self._credits_label.configure(text=f"{bal:.2f}")
                else:
                    self._credits_label.configure(text="—")
            self.after(0, _set)

        threading.Thread(target=_fetch, daemon=True).start()

    def _refresh_credits(self):
        """Manually refresh credits (only when Refresh button clicked)."""
        self._update_credits()

    def _update_activity(self):
        """Update activity log."""
        entries = self.worker.activity_log.get_recent(20)
        lines = []
        for e in reversed(entries):
            ts = e.get("timestamp", "")
            typ = e.get("type", "")
            details = e.get("details", "")
            if details:
                lines.append(f"[{ts}] {typ}: {details}")
            else:
                lines.append(f"[{ts}] {typ}")
        text = "\n".join(lines) if lines else "No activity yet."
        self._activity_text.configure(state="normal")
        self._activity_text.delete("1.0", "end")
        self._activity_text.insert("1.0", text)
        self._activity_text.configure(state="disabled")

    def _update_pause_buttons(self):
        """Update pause/resume button states."""
        if self.worker.is_paused():
            self._pause_btn.configure(state="disabled")
            self._resume_btn.configure(state="normal")
        else:
            self._pause_btn.configure(state="normal")
            self._resume_btn.configure(state="disabled")

    def _on_pause_toggle(self):
        """Toggle pause/resume."""
        if self.worker.is_paused():
            self.worker.resume()
        else:
            self.worker.pause()

    def _on_quit(self):
        """Gracefully shutdown worker and close app."""
        if self._shutting_down:
            return
        self._shutting_down = True

        if self._refresh_job:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

        if self.worker and not self.worker.is_paused():
            self.worker.pause()

        if self.loop:
            try:
                if self.worker_task:
                    self.loop.call_soon_threadsafe(self.worker_task.cancel)
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass

        if self.on_quit:
            self.on_quit()
