"""Launch Manhattan Mission Control (Streamlit)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    app_entry = root / "app" / "main.py"
    if not app_entry.exists():
        print(f"Streamlit app not found: {app_entry}")
        print("Run from repo root: streamlit run app/main.py")
        raise SystemExit(1)

    print("Starting Mission Control (Streamlit)…")
    print("  streamlit run app/main.py")

    env = {**os.environ}
    src = str(root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", str(root))

    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(app_entry)],
            cwd=str(root),
            env=env,
        )
    )


if __name__ == "__main__":
    main()
