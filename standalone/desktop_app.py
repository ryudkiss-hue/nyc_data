"""
Manhattan Mission Control — Native Desktop Wrapper
==================================================

Boots the Streamlit server on a background thread and renders it inside a
native OS window via pywebview — no browser tab, no visible localhost URL.

Works both as a plain script and as a PyInstaller-frozen .exe (``sys.frozen``).
Reads configuration from the same per-user env file the tkinter launcher
writes: ``%APPDATA%\\ManhattanMissionControl\\.env``.

Run directly:
    python standalone/desktop_app.py

Prerequisites:
    pip install pywebview streamlit
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution — identical contract to launcher.py
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).resolve().parent.parent

APP_SCRIPT = APP_ROOT / "app" / "app.py"
ENV_DIR = Path(os.environ.get("APPDATA", Path.home())) / "NYCDOTAnalystToolkit"
ENV_FILE = ENV_DIR / ".env"

WINDOW_TITLE = "NYC DOT SIM Analyst Toolkit"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _free_port(preferred: int = 8501) -> int:
    """Return `preferred` if free, otherwise an OS-assigned open port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

def _resolve_python() -> str:
    """Find a Python interpreter that can run Streamlit.

    When running as a normal script, ``sys.executable`` is the right Python.
    When frozen by PyInstaller, ``sys.executable`` is the .exe itself, so we
    fall back to a system Python discovered on PATH.
    """
    if not getattr(sys, "frozen", False):
        return sys.executable
    for candidate in ("pythonw.exe", "python.exe", "python3", "python"):
        found = shutil.which(candidate)
        if found:
            return found
    # Last resort — let the exe try (will error clearly if it can't)
    return sys.executable

def _load_env() -> dict[str, str]:
    """Read key=value pairs from the per-user env file."""
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def _wait_for_health(url: str, timeout: float = 45.0) -> bool:
    """Poll Streamlit's health endpoint until it responds or we time out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    return False

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
class StreamlitServer:
    """Owns the Streamlit subprocess and tears it down cleanly."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        if not APP_SCRIPT.exists():
            raise FileNotFoundError(f"Cannot find app entry point: {APP_SCRIPT}")

        env = os.environ.copy()
        env.update(_load_env())
        # Ensure imports resolve (src/ + repo root) and server stays headless
        existing_pp = env.get("PYTHONPATH", "")
        parts = [str(APP_ROOT / "src"), str(APP_ROOT)]
        if existing_pp:
            parts.append(existing_pp)
        env["PYTHONPATH"] = os.pathsep.join(parts)

        cmd = [
            _resolve_python(),
            "-m",
            "streamlit",
            "run",
            str(APP_SCRIPT),
            "--server.headless=true",
            "--server.port",
            str(self.port),
            "--server.address",
            "127.0.0.1",
            "--browser.gatherUsageStats",
            "false",
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW  # hide console window

        self.proc = subprocess.Popen(
            cmd,
            cwd=str(APP_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.kill()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    try:
        import webview  # pywebview
    except ImportError:
        print(
            "pywebview is not installed.\n"
            "  Install it with:  pip install pywebview\n"
            "  (On Linux you may also need: pip install pywebview[qt] or [gtk])",
            file=sys.stderr,
        )
        return 1

    port = _free_port(8501)
    url = f"http://127.0.0.1:{port}"
    health = f"{url}/_stcore/health"

    server = StreamlitServer(port)
    try:
        server.start()
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # Wait for readiness on a background thread so the window can show a splash.
    ready = {"ok": False}

    def _boot() -> None:
        ready["ok"] = _wait_for_health(health)

    boot_thread = threading.Thread(target=_boot, daemon=True)
    boot_thread.start()
    boot_thread.join(timeout=50)

    if not ready["ok"]:
        server.stop()
        print(
            "[ERROR] Streamlit did not become healthy in time. "
            "Check that dependencies are installed: "
            'pip install -e ".[mission,postgres,xlsx]"',
            file=sys.stderr,
        )
        return 1

    window = webview.create_window(
        WINDOW_TITLE,
        url,
        width=1480,
        height=940,
        min_size=(1024, 680),
        background_color="#0a1628",
    )

    # Ensure the server is torn down when the window closes.
    window.events.closed += server.stop

    try:
        webview.start()  # blocks until the window is closed
    finally:
        server.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
