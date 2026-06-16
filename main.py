"""Launch Manhattan Mission Control (Dash/FastAPI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent

    # PRIMARY: Dash Mission Control (FastAPI backend, Plotly charts, Mantine UI)
    dash_app = root / "app" / "dash_app.py"
    if dash_app.exists():
        print("Starting NYC DOT SIM Toolkit (Dash Mission Control)…")
        print("  python app/dash_app.py")
        print("  → http://localhost:8011")

        env = {**os.environ}
        src = str(root / "src")
        env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", str(root))

        raise SystemExit(
            subprocess.call(
                [sys.executable, str(dash_app)],
                cwd=str(root),
                env=env,
            )
        )

    # FALLBACK: Streamlit (if Dash not available)
    streamlit_app = root / "app" / "app.py"
    if streamlit_app.exists():
        print("Dash app not found. Falling back to Streamlit…")
        print("  streamlit run app/app.py")

        env = {**os.environ}
        src = str(root / "src")
        env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", str(root))

        raise SystemExit(
            subprocess.call(
                [sys.executable, "-m", "streamlit", "run", str(streamlit_app)],
                cwd=str(root),
                env=env,
            )
        )

    print("Error: Neither Dash (app/dash_app.py) nor Streamlit (app/app.py) app found.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
