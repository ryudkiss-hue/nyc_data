from __future__ import annotations

import time
from typing import Any, Callable

import requests


class SocrataToolkitError(Exception):
    pass


def with_retries(fn: Callable[[], requests.Response], retries: int = 3, backoff: float = 1.5) -> requests.Response:
    last_exc: Exception | None = None
    delay = 1.0
    for _ in range(retries):
        try:
            resp = fn()
            resp.raise_for_status()
            return resp
        except Exception as exc:  # network/server surface as clean toolkit error later
            last_exc = exc
            time.sleep(delay)
            delay *= backoff
    raise SocrataToolkitError(f"Request failed after {retries} retries: {last_exc}")


def normalize_formats(values: list[str]) -> list[str]:
    return [v.strip().lower() for v in values if v and v.strip()]
