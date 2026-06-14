"""Tests for socrata_toolkit.fair.cli."""

from __future__ import annotations

import json

from socrata_toolkit.fair.cli import main


def test_score_runs(capsys):
    rc = main(["score", "--registry", "config/datasets.yaml"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip()
    assert "overall" in out

def test_dcat_outputs_jsonld(capsys):
    rc = main(["dcat"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "@context" in payload
    assert payload["@type"] == "dcat:Catalog"
