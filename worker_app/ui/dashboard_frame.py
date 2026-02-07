"""
Dashboard - connection status, credits, pause/resume toggle, activity log,
job submission (code/file, language), and recent jobs with output viewer.
90s hacking terminal aesthetic.
"""

import os
import threading
from tkinter import filedialog
from typing import Optional, Callable, Any, List, Dict

import customtkinter as ctk

from .theme import (
    BG_DARK, BG_PANEL, BG_DARKEST, GREEN, GREEN_DIM, GREEN_BRIGHT, GREEN_GLOW,
    AMBER, CYAN, MAGENTA, RED, RED_BRIGHT, GRAY, GRAY_DARK, GRAY_LIGHT,
    TERMINAL_FONT, TERMINAL_FONT_SMALL, TERMINAL_FONT_LARGE, TERMINAL_FONT_MEGA,
    ANIM_CURSOR_BLINK, ANIM_PULSE_FAST, ANIM_PULSE_SLOW,
)

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
        self._idle_workers = None
        self._cursor_blink = True
        self._pulse_step = 0
        self._tab_glow = 0
        self._status_chars = ["[*]", "[+]", "[◉]", "[●]"]
        self._idle_pulse = 0
        self._anim_running = True

        self._build_ui()
        self._start_refresh()
        self._start_animations()
        # Initial workers fetch after short delay
        self.after(1500, self._update_workers)

    def _build_ui(self):
        """Build the dashboard UI - terminal style."""
        # Decorative top scan line
        top_border = ctk.CTkFrame(
            self, fg_color=GREEN_DIM, height=2, corner_radius=0
        )
        top_border.pack(fill="x", pady=(0, 2))
        
        # Header row: title left, idle workers right
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            header_frame,
            text=f"╔═══ GRID-X NODE // USER: {self.worker.user_id} ═══╗",
            font=TERMINAL_FONT_LARGE,
            text_color=GREEN,
        )
        title.pack(side="left")

        # Idle workers badge - top right
        self._idle_frame = ctk.CTkFrame(
            header_frame, fg_color=BG_PANEL,
            corner_radius=4, border_width=1, border_color=GREEN_DIM,
        )
        self._idle_frame.pack(side="right", padx=(10, 0))
        self._idle_label = ctk.CTkLabel(
            self._idle_frame,
            text="◉ IDLE WORKERS: -- ",
            font=TERMINAL_FONT,
            text_color=GREEN_DIM,
        )
        self._idle_label.pack(padx=12, pady=6)

        # Tabs - styled for terminal
        self._tabview = ctk.CTkTabview(
            self,
            fg_color=BG_PANEL,
            segmented_button_fg_color=BG_DARK,
            segmented_button_selected_color=GREEN_DIM,
            segmented_button_selected_hover_color=GREEN_DIM,
            segmented_button_unselected_color=BG_DARK,
            segmented_button_unselected_hover_color=BG_PANEL,
            text_color=GREEN,
            text_color_disabled=GRAY,
        )
        self._tabview.pack(fill="both", expand=True, pady=(0, 10))

        self._tab_status = self._tabview.add("[ ◆ STATUS ]")
        self._tab_submit = self._tabview.add("[ ◆ SUBMIT JOB ]")
        self._tab_jobs = self._tabview.add("[ ◆ JOB HISTORY ]")

        self._build_status_tab()
        self._build_submit_tab()
        self._build_jobs_tab()

        # Quit - terminal style with proper hover (text stays visible)
        self._terminate_btn = ctk.CTkButton(
            self, text="[ ◼ TERMINATE ]",
            command=self._on_quit, width=160, height=36,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color=BG_PANEL, text_color=RED_BRIGHT, 
            border_width=2, border_color=RED,
            hover_color=BG_DARKEST, hover=True,
            corner_radius=0,
        )
        self._terminate_btn.pack(pady=(10, 0))

    def _build_status_tab(self):
        """Status tab - terminal style."""
        self._tab_status.configure(fg_color=BG_DARK)
        status_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        status_frame.pack(fill="x", pady=(0, 10))

        self._status_indicator = ctk.CTkLabel(
            status_frame, text="[◉]", font=TERMINAL_FONT, text_color=CYAN,
        )
        self._status_indicator.pack(side="left", padx=(0, 8))
        self._status_text = ctk.CTkLabel(
            status_frame, text="CHECKING...", font=TERMINAL_FONT, text_color=AMBER,
        )
        self._status_text.pack(side="left")

        credits_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        credits_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(credits_frame, text="> CREDITS: ", font=TERMINAL_FONT, text_color=GREEN_DIM).pack(side="left")
        self._credits_label = ctk.CTkLabel(
            credits_frame, text="--", font=TERMINAL_FONT, text_color=GREEN,
        )
        self._credits_label.pack(side="left")
        self._refresh_credits_btn = ctk.CTkButton(
            credits_frame, text="[ ⟳ REFRESH ]", width=100, height=26,
            font=TERMINAL_FONT_SMALL, command=self._refresh_credits,
            fg_color=BG_PANEL, text_color=GREEN_DIM, border_width=1, border_color=GREEN_DIM,
        )
        self._refresh_credits_btn.pack(side="left", padx=(10, 0))

        toggle_frame = ctk.CTkFrame(self._tab_status, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(10, 15))

        self._pause_btn = ctk.CTkButton(
            toggle_frame, text="[ ◼ PAUSE ]", command=self._on_pause_toggle,
            width=110, height=34, font=TERMINAL_FONT_SMALL,
            fg_color=BG_PANEL, text_color=AMBER, border_width=1, border_color=AMBER,
        )
        self._pause_btn.pack(side="left", padx=(0, 8))

        self._resume_btn = ctk.CTkButton(
            toggle_frame, text="[ ▶ RESUME ]", command=self._on_pause_toggle,
            width=110, height=34, font=TERMINAL_FONT_SMALL, state="disabled",
            fg_color=BG_PANEL, text_color=GREEN_DIM, border_width=1, border_color=GREEN_DIM,
        )
        self._resume_btn.pack(side="left")

        ctk.CTkLabel(
            self._tab_status, text="> LOG:", font=TERMINAL_FONT,
            text_color=GREEN_DIM,
        ).pack(anchor="w", pady=(15, 5))
        self._activity_text = ctk.CTkTextbox(
            self._tab_status, height=200, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=BG_PANEL, text_color=GREEN, border_width=2, border_color=GREEN, corner_radius=0,
        )
        self._activity_text.pack(fill="both", expand=True, pady=(0, 10))

    def _build_submit_tab(self):
        """Submit job tab - terminal style."""
        self._tab_submit.configure(fg_color=BG_DARK)
        ctk.CTkLabel(
            self._tab_submit, text="> SOURCE:", font=TERMINAL_FONT, text_color=GREEN_DIM,
        ).pack(anchor="w", pady=(0, 5))
        self._code_text = ctk.CTkTextbox(
            self._tab_submit, height=120, wrap="word",
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=BG_PANEL, text_color=GREEN, border_width=2, border_color=GREEN, corner_radius=0,
        )
        self._code_text.pack(fill="x", pady=(0, 10))
        self._code_text.insert("1.0", "# EXECUTE REMOTE\nprint('Hello from Grid-X!')")

        btn_row = ctk.CTkFrame(self._tab_submit, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="[ ▤ LOAD FILE ]", width=120, font=TERMINAL_FONT_SMALL,
            command=self._load_code_from_file,
            fg_color=BG_PANEL, text_color=GREEN_DIM, border_width=1, border_color=GREEN_DIM,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(btn_row, text="LANG:", font=TERMINAL_FONT_SMALL, text_color=GREEN_DIM).pack(side="left", padx=(10, 5))
        self._language_var = ctk.StringVar(value="Python")
        self._language_menu = ctk.CTkOptionMenu(
            btn_row, values=[label for label, _ in LANGUAGES],
            variable=self._language_var, width=100,
            font=TERMINAL_FONT_SMALL,
            fg_color=BG_PANEL, button_color=GREEN_DIM, button_hover_color=GREEN,
            dropdown_fg_color=BG_PANEL, dropdown_text_color=GREEN,
        )
        self._language_menu.pack(side="left", padx=(0, 10))

        self._submit_btn = ctk.CTkButton(
            btn_row, text="[ EXECUTE ]", width=120, height=32,
            font=TERMINAL_FONT_SMALL, command=self._on_submit_job,
            fg_color=BG_PANEL, text_color=GREEN, border_width=1, border_color=GREEN,
        )
        self._submit_btn.pack(side="left")

        self._submit_status = ctk.CTkLabel(
            self._tab_submit, text="", font=TERMINAL_FONT_SMALL,
            text_color=AMBER, wraplength=400,
        )
        self._submit_status.pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(
            self._tab_submit, text="> OUTPUT:", font=TERMINAL_FONT, text_color=GREEN_DIM,
        ).pack(anchor="w", pady=(15, 5))
        self._submit_output = ctk.CTkTextbox(
            self._tab_submit, height=150, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=BG_PANEL, text_color=GREEN, border_width=1, border_color=GREEN_DIM,
        )
        self._submit_output.pack(fill="both", expand=True, pady=(0, 10))
        self._show_submit_output("> Awaiting execution...")

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
                self._submit_status.configure(text=f"[ OK ] Loaded: {os.path.basename(path)}", text_color=GREEN_DIM)
            except Exception as e:
                self._submit_status.configure(text=f"[ ERROR ] {e}", text_color=RED)

    def _on_submit_job(self):
        """Submit the code as a job."""
        code = self._code_text.get("1.0", "end").strip()
        if not code:
            self._submit_status.configure(text="[ ! ] Enter source code.", text_color=AMBER)
            return

        lang_val = self._get_language_value()

        if not self.worker.is_connected:
            self._submit_status.configure(text="[ X ] OFFLINE. Connect first.", text_color=RED)
            return

        self._submit_btn.configure(state="disabled")
        self._submit_status.configure(text="[ * ] Dispatching...", text_color=GREEN_DIM)
        self._show_submit_output("> Waiting for remote execution...")

        def _do_submit():
            try:
                job_id = self.worker.submit_job(code, language=lang_val, wait_for_result=False)
                if job_id:
                    from worker_app.job_history import add_job_to_history
                    add_job_to_history(self.worker.user_id, job_id, lang_val, code[:80])
                    def _ok():
                        self._submit_status.configure(text="[ OK ] Submitted. Awaiting result...", text_color=GREEN)
                        self._submit_btn.configure(state="normal")
                    self.after(0, _ok)
                    self._poll_job_and_show_result(job_id)
                else:
                    def _fail():
                        self._submit_status.configure(text="[ FAIL ] Check connection & credits.", text_color=RED)
                        self._submit_btn.configure(state="normal")
                        self._show_submit_output("> EXECUTION FAILED")
                    self.after(0, _fail)
            except Exception as e:
                def _err():
                    self._submit_status.configure(text=f"[ ERROR ] {e}", text_color=RED)
                    self._submit_btn.configure(state="normal")
                    self._show_submit_output(f"> ERROR: {e}")
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
        """Recent jobs tab - terminal style."""
        self._tab_jobs.configure(fg_color=BG_DARK)
        top_row = ctk.CTkFrame(self._tab_jobs, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(top_row, text="> JOB QUEUE:", font=TERMINAL_FONT, text_color=GREEN_DIM).pack(side="left")
        ctk.CTkButton(
            top_row, text="[ ⟳ REFRESH ]", width=100, font=TERMINAL_FONT_SMALL,
            command=self._update_jobs_list,
            fg_color=BG_PANEL, text_color=GREEN_DIM, border_width=1, border_color=GREEN_DIM,
        ).pack(side="right")

        self._jobs_frame = ctk.CTkScrollableFrame(
            self._tab_jobs, height=120,
            fg_color=BG_PANEL, scrollbar_button_color=GREEN_DIM, scrollbar_button_hover_color=GREEN,
        )
        self._jobs_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self._tab_jobs, text="> OUTPUT (select job):", font=TERMINAL_FONT, text_color=GREEN_DIM,
        ).pack(anchor="w", pady=(5, 5))
        self._output_text = ctk.CTkTextbox(
            self._tab_jobs, height=150, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=BG_PANEL, text_color=GREEN, border_width=2, border_color=GREEN, corner_radius=0,
        )
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
            ctk.CTkLabel(
                self._jobs_frame,
                text="> No jobs. Run [ SUBMIT ] tab.",
                font=TERMINAL_FONT_SMALL,
                text_color=GRAY,
            ).pack(anchor="w")
            return

        for j in jobs[:30]:
            job_id = j.get("job_id") or j.get("id", "?")
            status = j.get("status", "?")
            lang = j.get("language", "python")
            row = ctk.CTkFrame(self._jobs_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            color = GREEN if status == "completed" else (RED if status in ("failed", "error") else GRAY)
            lbl = ctk.CTkLabel(
                row,
                text=f"> {job_id[:12]}... | {status} | {lang}",
                font=TERMINAL_FONT_SMALL,
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
            self._status_indicator.configure(text_color=GREEN, text="[+]")
            self._status_text.configure(text="◉ ONLINE", text_color=GREEN)
        elif self.worker.is_paused():
            self._status_indicator.configure(text_color=AMBER, text="[=]")
            self._status_text.configure(text="◼ PAUSED", text_color=AMBER)
        else:
            self._status_indicator.configure(text_color=RED, text="[X]")
            self._status_text.configure(text="✗ OFFLINE", text_color=RED)

    def _update_credits(self):
        """Update credits display (fetch in thread to avoid blocking)."""
        def _fetch():
            bal = self.worker.get_credits()
            def _set():
                if bal is not None:
                    self._credits_label.configure(text=f"{bal:.2f}", text_color=GREEN)
                else:
                    self._credits_label.configure(text="--", text_color=GRAY)
            self.after(0, _set)

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_workers(self):
        """Fetch worker list and update idle count."""
        def _fetch():
            try:
                workers = self.worker.get_workers()
                idle = sum(1 for w in workers if w.get('status') == 'idle') if workers else None
                self._idle_workers = idle
            except Exception:
                self._idle_workers = None

        threading.Thread(target=_fetch, daemon=True).start()

    def _start_animations(self):
        """Start blinking cursor and status pulse animations."""
        self._animate_cursor()
        self._animate_status_pulse()
        self._animate_idle_glow()

    def _animate_cursor(self):
        """Blink cursor after idle count."""
        if self._shutting_down or not self._anim_running:
            return
        base = "◉ IDLE WORKERS: -- " if self._idle_workers is None else f"◉ IDLE WORKERS: {self._idle_workers} "
        self._idle_label.configure(text=base + ("_" if self._cursor_blink else " "))
        self._cursor_blink = not self._cursor_blink
        self.after(500, self._animate_cursor)

    def _animate_status_pulse(self):
        """Subtle pulse on status indicator when connected."""
        if self._shutting_down or not self._anim_running:
            return
        if self.worker.is_connected:
            self._pulse_step = (self._pulse_step + 1) % 4
            chars = self._status_chars
            self._status_indicator.configure(text=chars[self._pulse_step], text_color=GREEN)
        self.after(ANIM_PULSE_FAST, self._animate_status_pulse)

    def _refresh_credits(self):
        """Manually refresh credits and worker count (when Refresh button clicked)."""
        self._update_credits()
        self._update_workers()

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
        text = "\n".join(lines) if lines else "> No activity."
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

    def _animate_idle_glow(self):
        """Pulse the idle workers badge."""
        if self._shutting_down or not self._anim_running:
            return
        self._idle_pulse = (self._idle_pulse + 1) % 3
        colors = [CYAN, GREEN_BRIGHT, GREEN]
        try:
            self._idle_label.configure(text_color=colors[self._idle_pulse])
        except:
            pass
        self.after(ANIM_PULSE_SLOW, self._animate_idle_glow)

    def _on_quit(self):
        """Gracefully shutdown worker and close app."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._anim_running = False

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
