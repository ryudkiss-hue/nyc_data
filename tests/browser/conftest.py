"""Browser test fixtures — starts Dash server once per session as a subprocess."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_APP_ENTRY = _PROJECT_ROOT / "app" / "dash_app.py"
_APP_HOST = "127.0.0.1"
_APP_PORT = 8011
_STARTUP_TIMEOUT = 180  # seconds


def _server_ready(base_url: str) -> bool:
    try:
        return requests.get(base_url, timeout=2).status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def dash_base_url():
    """Start Dash Mission Control once per test session; kill it on teardown.

    If a server is already listening on port 8011 (e.g. dev running locally),
    the fixture reuses it and does not kill it on teardown.

    Server output is redirected to a temp file (not subprocess.PIPE) to prevent
    the pipe-buffer deadlock: uvicorn logs at debug level + the ingestion-poller
    firing every 2s generates enough output to fill a 64 KB pipe, blocking the
    server process and causing all subsequent page.goto() calls to timeout.
    """
    base = f"http://{_APP_HOST}:{_APP_PORT}"

    # Reuse an existing server — don't kill what we didn't start.
    if _server_ready(base):
        yield base
        return

    duckdb = os.environ.get(
        "DUCKDB_PATH",
        str(_PROJECT_ROOT / "nyc_dot_analytics.duckdb"),
    )
    env = {
        **os.environ,
        "DUCKDB_PATH": duckdb,
        "NYC_FORCE_LOCAL": "1",
    }

    # Write server stdout/stderr to a temp file — never use subprocess.PIPE for a
    # long-running server process, because unread pipe buffers cause deadlocks.
    _log_path = Path(tempfile.gettempdir()) / "dash_test_server.log"
    _log_fh = open(_log_path, "wb")

    proc = subprocess.Popen(
        [sys.executable, str(_APP_ENTRY)],
        env=env,
        stdout=_log_fh,
        stderr=subprocess.STDOUT,  # merge stderr → same file, no second pipe
    )

    deadline = time.monotonic() + _STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _log_fh.flush()
            log_tail = _log_path.read_text(errors="replace")[-3000:]
            pytest.fail(
                f"Dash server exited early (rc={proc.returncode}).\n"
                f"log: {log_tail}"
            )
        if _server_ready(base):
            break
        time.sleep(1)
    else:
        proc.kill()
        _log_fh.flush()
        log_tail = _log_path.read_text(errors="replace")[-3000:]
        pytest.fail(
            f"Dash server did not become ready within {_STARTUP_TIMEOUT}s.\n"
            f"log: {log_tail}"
        )

    yield base

    proc.kill()
    _log_fh.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
