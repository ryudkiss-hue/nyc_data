"""Entry stub — primary GUI is dash_app/app.py. Legacy NiceGUI is opt-in."""

from __future__ import annotations

import os
import sys


def main() -> None:
    if os.getenv("NYC_DOT_LEGACY_NICEGUI", "").lower() in ("1", "true", "yes"):
        root = os.path.dirname(os.path.abspath(__file__))
        target = os.path.join(root, "legacy", "nicegui_mission_control.py")
        import runpy

        runpy.run_path(target, run_name="__main__")
        return

    print("Primary dashboard: python dash_app/app.py  →  http://127.0.0.1:8050")
    print("Legacy NiceGUI:    set NYC_DOT_LEGACY_NICEGUI=1  then  python app.py")
    print("Guide:             docs/SIMPLE_START.md")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
