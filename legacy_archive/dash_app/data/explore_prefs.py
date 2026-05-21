"""Persist Explore page slider/checkbox preferences per toolkit profile."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _prefs_path() -> Path:
    prof = (os.getenv("TOOLKIT_PROFILE", "") or "default").strip() or "default"
    root = Path("outputs/.state")
    if prof:
        return root / "profiles" / prof / "explore_prefs.json"
    return root / "explore_prefs.json"


def load_explore_prefs() -> dict[str, Any]:
    path = _prefs_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_explore_prefs(prefs: dict[str, Any]) -> Path:
    path = _prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    return path
