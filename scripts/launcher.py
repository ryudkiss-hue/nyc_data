"""Launcher compatibility shim for the NYC DOT Socrata Toolkit."""

from __future__ import annotations

import sys


def main(args: list[str] | None = None) -> None:
    """Entry point for the launcher shim.

    Forwards to the CLI when a real command is given; prints help and exits 0
    when 'help' is passed.
    """
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print("NYC DOT Socrata Toolkit — use `socrata --help` for full command reference.")
        sys.exit(0)

    from socrata_toolkit.core.cli import main as cli_main

    cli_main(args, standalone_mode=True)


if __name__ == "__main__":
    main()
