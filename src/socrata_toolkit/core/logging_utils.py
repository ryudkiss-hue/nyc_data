from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_logger(name: str = "socrata_toolkit") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def write_run_report(path: str, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def redact_secrets(value: str) -> str:
    for key in ["password", "token", "secret", "apikey", "api_key"]:
        value = value.replace(key, "[REDACTED_KEY]")
    return value
