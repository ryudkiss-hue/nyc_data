"""Append-only ingestion telemetry for Mission Control support."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOG_PATH = _REPO_ROOT / "outputs" / "logs" / "ingest.jsonl"

def log_event(event: str, **fields: Any) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.time(), "event": event, **fields}
    with _LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
