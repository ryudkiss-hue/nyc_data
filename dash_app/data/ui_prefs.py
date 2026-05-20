"""Persist Dash UI preferences (theme, font scale, sidebar, offline run flag)."""



from __future__ import annotations



import json

import os

from pathlib import Path

from typing import Any



from dash_app.data.explore_prefs import load_explore_prefs, save_explore_prefs





def _prefs_path() -> Path:

    prof = (os.getenv("TOOLKIT_PROFILE", "") or "default").strip() or "default"

    root = Path("outputs/.state")

    if prof:

        return root / "profiles" / prof / "ui_prefs.json"

    return root / "ui_prefs.json"





def load_ui_prefs() -> dict[str, Any]:

    path = _prefs_path()

    if not path.exists():

        return {}

    try:

        return json.loads(path.read_text(encoding="utf-8"))

    except Exception:

        return {}





def save_ui_prefs(prefs: dict[str, Any]) -> Path:

    path = _prefs_path()

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")

    return path





def get_ui_pref(key: str, default: Any = None) -> Any:

    return load_ui_prefs().get(key, default)





def export_all_prefs() -> dict[str, Any]:

    return {

        "ui": load_ui_prefs(),

        "explore": load_explore_prefs(),

        "profile": (os.getenv("TOOLKIT_PROFILE", "") or "default").strip() or "default",

    }





def import_all_prefs(data: dict[str, Any]) -> None:

    if "ui" in data and isinstance(data["ui"], dict):

        save_ui_prefs(data["ui"])

    if "explore" in data and isinstance(data["explore"], dict):

        save_explore_prefs(data["explore"])

    prof = data.get("profile")

    if prof:

        os.environ["TOOLKIT_PROFILE"] = str(prof).strip()


