"""PyInstaller entry: delegates to socrata CLI, install wizard, or optional Dash GUI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

def _parse_flag(args: list[str], flag: str) -> bool:
    return flag in args

def _parse_option(args: list[str], flag: str) -> str | None:
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(f"{flag}="):
            return a.split("=", 1)[1]
    return None

def _run_dash() -> None:
    """Start Streamlit Mission Control, legacy Dash, or open Getting Started."""
    root = _app_root()
    getting_started = root / "docs" / "GETTING_STARTED.md"
    streamlit_script = root / "app" / "app.py"
    dash_script = root / "legacy_archive" / "dash_app" / "app.py"
    py = shutil.which("python") or shutil.which("py")
    env = {**os.environ, "PYTHONPATH": str(root / "src") + os.pathsep + str(root)}

    if py and streamlit_script.exists():
        print("Starting Mission Control (Streamlit)…")
        raise SystemExit(
            subprocess.call([py, "-m", "streamlit", "run", str(streamlit_script)], cwd=root, env=env)
        )

    if py and dash_script.exists():
        print(f"Starting legacy Dash via {py} …")
        raise SystemExit(subprocess.call([py, str(dash_script)], cwd=root, env=env))

    msg = (
        "GUI is not bundled in the standalone executable.\n"
        "Options:\n"
        "  • pip install -e \".[mission]\" && streamlit run app/app.py\n"
        "  • Legacy Dash: python legacy_archive/dash_app/app.py\n"
        "  • Use Docker: docker compose --profile analyst up -d\n"
        f"  • Read: {getting_started}\n"
    )
    print(msg, file=sys.stderr)
    if sys.platform.startswith("win") and getting_started.exists():
        os.startfile(str(getting_started))  # noqa: S606
        return
    raise SystemExit(1)

def _run_wizard(args: list[str]) -> None:
    from socrata_toolkit.install_wizard import _print_summary, run_wizard

    root_opt = _parse_option(args, "--root")
    root = Path(root_opt).resolve() if root_opt else _app_root()
    summary = run_wizard(
        root=root,
        non_interactive=_parse_flag(args, "--non-interactive"),
        skip_checks=_parse_flag(args, "--skip-checks"),
        force_profile=_parse_flag(args, "--force-profile"),
    )
    _print_summary(summary)

def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(
            "NYC DOT Sidewalk Toolkit\n"
            "  nyc-dot-toolkit.exe wizard [--non-interactive] [--root DIR]\n"
            "  nyc-dot-toolkit.exe doctor\n"
            "  nyc-dot-toolkit.exe analyst run --profile config\\analyst_profile.yaml\n"
            "  nyc-dot-toolkit.exe dash\n"
            "  nyc-dot-toolkit.exe <socrata subcommand> ...\n"
        )
        return
    if args[0] == "setup" and len(args) > 1 and args[1] == "wizard":
        _run_wizard(args[2:])
        return
    if args[0] == "wizard":
        _run_wizard(args[1:])
        return
    if args[0] == "dash":
        _run_dash()
        return
    if args[0] == "doctor":
        sys.argv = ["socrata", "doctor", "--check-db"]
        from socrata_toolkit.core.cli import main as cli_main

        cli_main()
        return
    from socrata_toolkit.core.cli import main as cli_main

    sys.argv = ["socrata"] + args
    cli_main()

if __name__ == "__main__":
    main()
