"""Dash UI state persistence.

This is file-based (outputs/.state) to support:
- task scheduler runs updating state
- multiple entry points (CLI, Dash, EXE) sharing "last run" context
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import json


def _state_path() -> Path:
    prof = (os.getenv("TOOLKIT_PROFILE", "") or "default").strip()
    if prof:
        p = Path("outputs/.state/profiles") / prof / "last_pack.json"
        if p.exists():
            return p
    return Path("outputs/.state/last_pack.json")


def load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def state_value(key: str, default: Any = "") -> Any:
    return load_state().get(key, default)


def save_state(data: dict[str, Any]) -> Path:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def update_state(**kwargs: Any) -> dict[str, Any]:
    data = load_state()
    data.update(kwargs)
    save_state(data)
    return data

