from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_local_config(path: str | None = None) -> dict[str, Any]:
    candidates = [Path(path)] if path else [Path.cwd() / "socrata_toolkit.config.json", Path.home() / ".socrata_toolkit.config.json"]
    for c in candidates:
        if c and c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    return {}


def get_default(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = config
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
