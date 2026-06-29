"""Launcher compatibility shim."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy CLI test - command removed")


def test_launcher_help_exits_zero():
    import launcher

    with pytest.raises(SystemExit) as exc:
        launcher.main(["help"])
    assert exc.value.code == 0


def test_launcher_doctor_via_cli():
    from click.testing import CliRunner

    from socrata_toolkit.core.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
