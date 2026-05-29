"""Launch Manhattan Mission Control (Streamlit) — thin launcher shim.

Usage:
    python main.py                     # standard launch
    streamlit run app/mission_control.py  # direct Streamlit launch
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    app_entry = root / "app" / "mission_control.py"

    if not app_entry.exists():
        # Fallback for legacy deploys
        fallback = root / "app" / "main.py"
        if fallback.exists():
            app_entry = fallback
        else:
            print(f"Streamlit app not found: {app_entry}")
            raise SystemExit(1)

    print("Starting Manhattan Mission Control…")
    print(f"  streamlit run {app_entry.relative_to(root)}")

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
