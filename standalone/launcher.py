"""
Manhattan Mission Control — Windows Desktop Launcher
A tkinter 4-page wizard that installs, configures, and launches the Streamlit app.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

# ---------------------------------------------------------------------------
# Path resolution — works both as .py and as PyInstaller-frozen .exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).resolve().parent.parent

STREAMLIT_URL = "http://localhost:8501"
HEALTH_URL = "http://localhost:8501/_stcore/health"
ENV_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ManhattanMissionControl"
ENV_FILE = ENV_DIR / ".env"

# ---------------------------------------------------------------------------
# Theme colours
# ---------------------------------------------------------------------------
BG = "#0a1628"
ACCENT = "#f4c430"
FG = "#e8eef4"
SUBTITLE = "#9eb3c7"
ENTRY_BG = "#1a2332"
BTN_ACTIVE = "#c9a020"
FONT_FAMILY = "Segoe UI"


def make_font(size: int = 10, bold: bool = False) -> tuple:
    weight = "bold" if bold else "normal"
    return (FONT_FAMILY, size, weight)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_env() -> dict[str, str]:
    """Read key=value pairs from ENV_FILE, ignoring blank / comment lines."""
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
    return values


def write_env(values: dict[str, str]) -> None:
    ENV_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in values.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def wait_for_health(timeout: int = 30) -> bool:
    """Poll /_stcore/health until 200 OK or timeout."""
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# Main launcher window
# ---------------------------------------------------------------------------

class Launcher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Manhattan Mission Control — Launcher")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._set_icon()
        self._center(720, 540)

        self._server_proc: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._monitor_after_id: str | None = None

        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill=tk.BOTH, expand=True)

        self._pages: list[tk.Frame] = []
        self._current_page = 0

        self._build_pages()
        self._show_page(0)

    # ------------------------------------------------------------------
    # Geometry / icon helpers
    # ------------------------------------------------------------------

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _set_icon(self) -> None:
        icon_path = APP_ROOT / "standalone" / "icons" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Page management
    # ------------------------------------------------------------------

    def _build_pages(self) -> None:
        for page_cls in (WelcomePage, ConfigPage, InstallPage, RunningPage):
            page = page_cls(self._container, self)
            page.place(relwidth=1, relheight=1)
            self._pages.append(page)

    def _show_page(self, index: int) -> None:
        self._pages[index].tkraise()
        self._current_page = index
        if hasattr(self._pages[index], "on_show"):
            self._pages[index].on_show()  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Public navigation helpers used by pages
    # ------------------------------------------------------------------

    def go_to_config(self) -> None:
        self._show_page(1)

    def go_to_install(self) -> None:
        self._show_page(2)

    def go_to_running(self) -> None:
        self._show_page(3)

    def go_to_welcome(self) -> None:
        self._show_page(0)

    def stop_server(self) -> None:
        if self._monitor_after_id:
            self.after_cancel(self._monitor_after_id)
            self._monitor_after_id = None
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
        self._server_proc = None

    def on_closing(self) -> None:
        self.stop_server()
        self.destroy()


# ---------------------------------------------------------------------------
# Page 0 — Welcome
# ---------------------------------------------------------------------------

class WelcomePage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: Launcher) -> None:
        super().__init__(parent, bg=BG)
        self._app = app
        self._build()

    def _build(self) -> None:
        pad = {"padx": 40, "pady": 6}

        tk.Label(
            self,
            text="🗽  Manhattan Mission Control",
            font=make_font(22, bold=True),
            bg=BG,
            fg=ACCENT,
        ).pack(pady=(50, 4))

        tk.Label(
            self,
            text="NYC Sidewalk Inspection & AI Analytics Platform",
            font=make_font(11),
            bg=BG,
            fg=SUBTITLE,
        ).pack(**pad)

        separator = tk.Frame(self, bg=ACCENT, height=2, width=400)
        separator.pack(pady=20)

        features = [
            "🔍  Real-time Socrata open-data integration",
            "🤖  Multi-model AI assistant (Gemini · OpenAI · Ollama)",
            "📊  Interactive maps, charts & executive reports",
            "💾  Local DuckDB caching — works offline",
            "🚀  One-click local Streamlit server",
        ]
        for feat in features:
            tk.Label(
                self,
                text=feat,
                font=make_font(10),
                bg=BG,
                fg=FG,
                anchor="w",
            ).pack(fill=tk.X, **pad)

        tk.Frame(self, bg=BG).pack(expand=True)

        btn = tk.Button(
            self,
            text="Get Started  →",
            font=make_font(12, bold=True),
            bg=ACCENT,
            fg=BG,
            activebackground=BTN_ACTIVE,
            activeforeground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=10,
            command=self._app.go_to_config,
        )
        btn.pack(pady=(0, 40))


# ---------------------------------------------------------------------------
# Page 1 — Configuration
# ---------------------------------------------------------------------------

FIELDS = [
    ("SOCRATA_APP_TOKEN", "Socrata App Token", True),
    ("GEMINI_API_KEY", "Gemini API Key", True),
    ("OPENAI_API_KEY", "OpenAI API Key", True),
    ("OLLAMA_HOST", "Ollama Host", False),
]


class ConfigPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: Launcher) -> None:
        super().__init__(parent, bg=BG)
        self._app = app
        self._entries: dict[str, tk.Entry] = {}
        self._show_vars: dict[str, tk.BooleanVar] = {}
        self._demo_var = tk.BooleanVar()
        self._build()

    def on_show(self) -> None:
        """Populate fields from .env each time the page is shown."""
        stored = read_env()
        for key, _, _ in FIELDS:
            if key in stored:
                entry = self._entries[key]
                entry.config(state=tk.NORMAL)
                entry.delete(0, tk.END)
                entry.insert(0, stored[key])
                # Re-apply masking
                show = self._show_vars[key].get()
                entry.config(show="" if show else "*")
        if "FORCE_DEMO_MODE" in stored:
            self._demo_var.set(stored["FORCE_DEMO_MODE"].lower() in ("1", "true", "yes"))

    def _build(self) -> None:
        tk.Label(
            self,
            text="Configuration",
            font=make_font(18, bold=True),
            bg=BG,
            fg=ACCENT,
        ).pack(pady=(30, 4))

        tk.Label(
            self,
            text=f"Settings are saved to  {ENV_FILE}",
            font=make_font(9),
            bg=BG,
            fg=SUBTITLE,
        ).pack(pady=(0, 16))

        form = tk.Frame(self, bg=BG)
        form.pack(fill=tk.X, padx=60)

        for row_idx, (key, label, sensitive) in enumerate(FIELDS):
            tk.Label(
                form,
                text=label,
                font=make_font(10),
                bg=BG,
                fg=FG,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="w", pady=4)

            show_var = tk.BooleanVar(value=False)
            self._show_vars[key] = show_var

            entry = tk.Entry(
                form,
                font=make_font(10),
                bg=ENTRY_BG,
                fg=FG,
                insertbackground=FG,
                relief=tk.FLAT,
                width=36,
                show="*" if sensitive else "",
            )
            entry.grid(row=row_idx, column=1, padx=(12, 6), pady=4)
            self._entries[key] = entry

            if sensitive:
                chk = tk.Checkbutton(
                    form,
                    text="Show",
                    variable=show_var,
                    font=make_font(9),
                    bg=BG,
                    fg=SUBTITLE,
                    activebackground=BG,
                    activeforeground=FG,
                    selectcolor=ENTRY_BG,
                    command=lambda e=entry, v=show_var: e.config(show="" if v.get() else "*"),
                )
                chk.grid(row=row_idx, column=2, sticky="w")

        # Demo mode checkbox
        demo_row = len(FIELDS)
        tk.Label(
            form,
            text="Force Demo Mode",
            font=make_font(10),
            bg=BG,
            fg=FG,
            anchor="w",
        ).grid(row=demo_row, column=0, sticky="w", pady=(12, 4))

        tk.Checkbutton(
            form,
            variable=self._demo_var,
            bg=BG,
            activebackground=BG,
            selectcolor=ENTRY_BG,
        ).grid(row=demo_row, column=1, sticky="w", padx=(12, 0), pady=(12, 4))

        form.grid_columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=24)

        tk.Button(
            btn_frame,
            text="← Back",
            font=make_font(10),
            bg=ENTRY_BG,
            fg=FG,
            activebackground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=self._app.go_to_welcome,
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame,
            text="Save & Install  →",
            font=make_font(11, bold=True),
            bg=ACCENT,
            fg=BG,
            activebackground=BTN_ACTIVE,
            activeforeground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=24,
            pady=8,
            command=self._save_and_continue,
        ).pack(side=tk.LEFT, padx=8)

    def _save_and_continue(self) -> None:
        values: dict[str, str] = {}
        for key, _, _ in FIELDS:
            val = self._entries[key].get().strip()
            if val:
                values[key] = val
        if self._demo_var.get():
            values["FORCE_DEMO_MODE"] = "1"
        write_env(values)
        self._app.go_to_install()


# ---------------------------------------------------------------------------
# Page 2 — Install & Launch
# ---------------------------------------------------------------------------

class InstallPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: Launcher) -> None:
        super().__init__(parent, bg=BG)
        self._app = app
        self._build()

    def on_show(self) -> None:
        self._log_widget.config(state=tk.NORMAL)
        self._log_widget.delete("1.0", tk.END)
        self._log_widget.config(state=tk.DISABLED)
        self._btn_continue.config(state=tk.DISABLED)
        threading.Thread(target=self._run_install, daemon=True).start()

    def _build(self) -> None:
        tk.Label(
            self,
            text="Installing & Starting",
            font=make_font(18, bold=True),
            bg=BG,
            fg=ACCENT,
        ).pack(pady=(30, 4))

        tk.Label(
            self,
            text="Installing dependencies and launching the Streamlit server…",
            font=make_font(10),
            bg=BG,
            fg=SUBTITLE,
        ).pack(pady=(0, 12))

        self._log_widget = scrolledtext.ScrolledText(
            self,
            font=("Consolas", 9),
            bg="#0d1f33",
            fg="#b0c4de",
            insertbackground=FG,
            relief=tk.FLAT,
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self._log_widget.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 12))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(0, 20))

        tk.Button(
            btn_frame,
            text="← Reconfigure",
            font=make_font(10),
            bg=ENTRY_BG,
            fg=FG,
            activebackground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=self._app.go_to_config,
        ).pack(side=tk.LEFT, padx=8)

        self._btn_continue = tk.Button(
            btn_frame,
            text="Open Dashboard  →",
            font=make_font(11, bold=True),
            bg=ACCENT,
            fg=BG,
            activebackground=BTN_ACTIVE,
            activeforeground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=24,
            pady=8,
            state=tk.DISABLED,
            command=self._app.go_to_running,
        )
        self._btn_continue.pack(side=tk.LEFT, padx=8)

    def _append_log(self, text: str) -> None:
        self._log_widget.config(state=tk.NORMAL)
        self._log_widget.insert(tk.END, text)
        self._log_widget.see(tk.END)
        self._log_widget.config(state=tk.DISABLED)

    def _run_install(self) -> None:
        self._append_log("=== Installing dependencies ===\n\n")
        python_exe = sys.executable
        pip_cmd = [python_exe, "-m", "pip", "install", "-e", ".[mission,postgres,xlsx]"]

        try:
            proc = subprocess.Popen(
                pip_cmd,
                cwd=str(APP_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in iter(proc.stdout.readline, ""):  # type: ignore[union-attr]
                self.after(0, self._append_log, line)
            proc.wait()
            if proc.returncode != 0:
                self.after(0, self._append_log, f"\n[ERROR] pip exited with code {proc.returncode}\n")
                return
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._append_log, f"\n[ERROR] {exc}\n")
            return

        self.after(0, self._append_log, "\n=== Starting Streamlit server ===\n\n")

        app_script = APP_ROOT / "app" / "mission_control.py"
        if not app_script.exists():
            self.after(
                0,
                self._append_log,
                f"[ERROR] Could not find {app_script}\n",
            )
            return

        env = os.environ.copy()
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()

        streamlit_cmd = [
            python_exe,
            "-m",
            "streamlit",
            "run",
            str(app_script),
            "--server.headless=true",
            "--server.port=8501",
        ]

        try:
            self._app._server_proc = subprocess.Popen(  # noqa: SLF001
                streamlit_cmd,
                cwd=str(APP_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._append_log, f"[ERROR] Could not start server: {exc}\n")
            return

        # Stream server startup output while waiting for health
        def stream_and_wait() -> None:
            proc = self._app._server_proc  # noqa: SLF001
            assert proc is not None  # noqa: S101
            ready = False
            deadline = time.time() + 30
            while time.time() < deadline and proc.poll() is None:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                if line:
                    self.after(0, self._append_log, line)
                # Check health in parallel
                import urllib.error
                import urllib.request

                try:
                    with urllib.request.urlopen(HEALTH_URL, timeout=1) as resp:
                        if resp.status == 200:
                            ready = True
                            break
                except Exception:  # noqa: BLE001
                    pass
            if ready:
                self.after(0, self._on_server_ready)
            else:
                self.after(
                    0,
                    self._append_log,
                    "\n[WARNING] Server did not respond within 30 s — you can still try opening the dashboard.\n",
                )
                self.after(0, lambda: self._btn_continue.config(state=tk.NORMAL))

        threading.Thread(target=stream_and_wait, daemon=True).start()

    def _on_server_ready(self) -> None:
        self._append_log("\n✔  Server is ready!\n")
        self._btn_continue.config(state=tk.NORMAL)
        self._app.go_to_running()


# ---------------------------------------------------------------------------
# Page 3 — Running
# ---------------------------------------------------------------------------

class RunningPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: Launcher) -> None:
        super().__init__(parent, bg=BG)
        self._app = app
        self._build()

    def on_show(self) -> None:
        webbrowser.open(STREAMLIT_URL)
        self._schedule_health_check()

    def _build(self) -> None:
        tk.Label(
            self,
            text="✔",
            font=make_font(64, bold=True),
            bg=BG,
            fg="#3ddc84",
        ).pack(pady=(60, 4))

        tk.Label(
            self,
            text="Mission Control is Running",
            font=make_font(20, bold=True),
            bg=BG,
            fg=ACCENT,
        ).pack(pady=(0, 8))

        url_label = tk.Label(
            self,
            text=STREAMLIT_URL,
            font=make_font(13),
            bg=BG,
            fg="#5ba3f5",
            cursor="hand2",
        )
        url_label.pack()
        url_label.bind("<Button-1>", lambda _: webbrowser.open(STREAMLIT_URL))

        self._status_label = tk.Label(
            self,
            text="Server: online",
            font=make_font(10),
            bg=BG,
            fg=SUBTITLE,
        )
        self._status_label.pack(pady=(16, 0))

        tk.Frame(self, bg=BG).pack(expand=True)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(0, 40))

        tk.Button(
            btn_frame,
            text="🌐  Open Browser",
            font=make_font(11, bold=True),
            bg=ACCENT,
            fg=BG,
            activebackground=BTN_ACTIVE,
            activeforeground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=lambda: webbrowser.open(STREAMLIT_URL),
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame,
            text="⚙  Reconfigure",
            font=make_font(10),
            bg=ENTRY_BG,
            fg=FG,
            activebackground=BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=8,
            command=self._reconfigure,
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame,
            text="■  Stop Server",
            font=make_font(10),
            bg="#5a1a1a",
            fg="#ff6b6b",
            activebackground="#3d0000",
            activeforeground="#ff6b6b",
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=8,
            command=self._stop_server,
        ).pack(side=tk.LEFT, padx=8)

    def _schedule_health_check(self) -> None:
        self._app._monitor_after_id = self.after(2000, self._health_check)  # noqa: SLF001

    def _health_check(self) -> None:
        import urllib.error
        import urllib.request

        proc = self._app._server_proc  # noqa: SLF001
        if proc is not None and proc.poll() is not None:
            self._status_label.config(text="Server: stopped ✖", fg="#ff6b6b")
            messagebox.showwarning(
                "Server stopped",
                "The Streamlit server has stopped unexpectedly.",
            )
            return
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    self._status_label.config(text="Server: online  ✔", fg="#3ddc84")
        except Exception:  # noqa: BLE001
            self._status_label.config(text="Server: unreachable !", fg=ACCENT)
        self._schedule_health_check()

    def _reconfigure(self) -> None:
        self._app.stop_server()
        self._app.go_to_config()

    def _stop_server(self) -> None:
        self._app.stop_server()
        self._status_label.config(text="Server: stopped", fg=SUBTITLE)
        messagebox.showinfo("Stopped", "The Streamlit server has been stopped.")
        self._app.go_to_welcome()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = Launcher()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
