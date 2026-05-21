"""Non-blocking subprocess helpers for Dash callbacks."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import subprocess
from typing import Sequence

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="nyc-dash")


def run_subprocess(
    cmd: Sequence[str],
    *,
    cwd: str,
    timeout: int,
) -> Future[subprocess.CompletedProcess[str]]:
    """Run a subprocess on a worker thread so Flask/Dash stays responsive."""

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

    return _executor.submit(_run)
