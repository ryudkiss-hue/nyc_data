"""PyInstaller entry: delegates to socrata CLI or install wizard."""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(
            "NYC DOT Sidewalk Toolkit\n"
            "  nyc-dot-toolkit.exe setup wizard   — configuration wizard\n"
            "  nyc-dot-toolkit.exe doctor         — health check\n"
            "  nyc-dot-toolkit.exe analyst run --profile config/analyst_profile.yaml\n"
            "  nyc-dot-toolkit.exe <socrata subcommand> ...\n"
        )
        return
    if args[0] == "setup" and len(args) > 1 and args[1] == "wizard":
        from socrata_toolkit.install_wizard import _print_summary, run_wizard

        _print_summary(run_wizard())
        return
    if args[0] == "wizard":
        from socrata_toolkit.install_wizard import _print_summary, run_wizard

        _print_summary(run_wizard())
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
