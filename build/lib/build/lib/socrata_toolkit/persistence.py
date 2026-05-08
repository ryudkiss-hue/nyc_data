from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_STORE = Path.home() / ".socrata_toolkit_pipelines.json"


def load_pipelines() -> dict[str, Any]:
    if not _STORE.exists():
        return {}
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_pipeline(name: str, config: dict) -> None:
    d = load_pipelines()
    d[name] = config
    _STORE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def delete_pipeline(name: str) -> None:
    d = load_pipelines()
    if name in d:
        del d[name]
        _STORE.write_text(json.dumps(d, indent=2), encoding="utf-8")
