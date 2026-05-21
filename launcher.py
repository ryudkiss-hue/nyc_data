"""Backward-compatible launcher — Mission Control (Streamlit) and socrata CLI."""

from __future__ import annotations

import sys


def _print_help() -> None:
    print("NYC DOT Toolkit launcher")
    print("  python launcher.py           # Mission Control (Streamlit)")
    print("  python launcher.py web         # same as above")
    print("  python launcher.py cli …       # socrata extended CLI")
    print("  python launcher.py doctor      # health + readiness")
    print("  python launcher.py setup all   # install wizard")
    print("Recommended: python main.py  |  mission  |  socrata …")


def main(argv: list[str] | None = None) -> None:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"web", "mission", "streamlit"}:
        import main as mission_entry

        mission_entry.main()
        return
    if args[0] == "cli":
        from socrata_toolkit.core.cli import main as cli_main

        sys.argv = ["socrata", *args[1:]]
        raise SystemExit(cli_main())
    if args[0] == "doctor":
        from socrata_toolkit.core.cli import main as cli_main

        sys.argv = ["socrata", "doctor", *args[1:]]
        raise SystemExit(cli_main())
    if args[0] == "setup":
        from socrata_toolkit.core.cli import main as cli_main

        sys.argv = ["socrata", "setup", *args[1:]]
        raise SystemExit(cli_main())
    if args[0] == "docker":
        print("Docker Compose stack was removed from this repo.")
        print("Mission Control image: docker build -f Dockerfile.mission -t nyc-mission .")
        print("Run: docker run -p 8501:8501 -e SOCRATA_APP_TOKEN=... nyc-mission")
        raise SystemExit(0)
    if args[0] in {"info", "help", "--help", "-h"}:
        _print_help()
        raise SystemExit(0)
    print(f"Unknown launcher command: {args[0]}")
    _print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
