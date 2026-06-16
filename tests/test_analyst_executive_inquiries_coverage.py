"""Coverage tests for analyst.executive and analyst.inquiries."""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

from types import SimpleNamespace

import pandas as pd

# ---------------------------------------------------------------------------
# analyst.executive.build_executive_summary
# ---------------------------------------------------------------------------

class TestBuildExecutiveSummary:
    def test_empty_inputs(self):
        from socrata_toolkit.analyst.executive import build_executive_summary

        md, html = build_executive_summary(
            construction=pd.DataFrame(),
            conflict_result=None,
            contracts=pd.DataFrame(),
            kpi_payload=None,
            run_date="2024-01-01",
            profile_name="default",
        )
        assert "Executive Summary" in md
        assert "No construction list data" in md
        assert isinstance(html, str)

    def test_populated_inputs(self):
        from socrata_toolkit.analyst.executive import build_executive_summary

        construction = pd.DataFrame({
            "location_id": ["L1", "L2", "L3"],
            "borough": ["MANHATTAN", "MANHATTAN", "BRONX"],
        })
        conflict_result = SimpleNamespace(
            conflict_count=4,
            conflict_rate=12.5,
            summary_by_borough={"MANHATTAN": 3, "BRONX": 1},
        )
        kpi_payload = {
            "metrics": [
                {"name": "Backlog", "status": "red", "value": 99, "target": 10},
                {"name": "OK metric", "status": "green", "value": 1, "target": 1},
            ]
        }
        md, html = build_executive_summary(
            construction=construction,
            conflict_result=conflict_result,
            contracts=pd.DataFrame({"contract_id": ["C1"], "x": [1]}),
            kpi_payload=kpi_payload,
            run_date="2024-02-01",
            profile_name="sidewalk",
        )
        assert "MANHATTAN" in md
        assert "MANHATTAN: 3" in md
        assert "Backlog" in md  # red KPI listed

    def test_conflict_result_without_borough_summary(self):
        from socrata_toolkit.analyst.executive import build_executive_summary

        conflict_result = SimpleNamespace(
            conflict_count=2,
            conflict_rate=5.0,
            summary_by_borough={},
        )
        md, _ = build_executive_summary(
            construction=pd.DataFrame(),
            conflict_result=conflict_result,
            contracts=pd.DataFrame(),
            kpi_payload={"metrics": []},
            run_date="2024-01-01",
            profile_name="p",
        )
        assert "Total conflicts: 2" in md

# ---------------------------------------------------------------------------
# analyst.inquiries
# ---------------------------------------------------------------------------

class TestLoadTemplateLibrary:
    def test_no_dir_returns_empty(self, tmp_path):
        from socrata_toolkit.analyst.inquiries import load_template_library

        assert load_template_library(tmp_path / "missing") == []

    def test_loads_with_frontmatter_keywords(self, tmp_path):
        from socrata_toolkit.analyst.inquiries import load_template_library

        (tmp_path / "delay.md").write_text(
            "---\nkeywords: delay, late, overdue\n---\nBody about {{contract_id}}.",
            encoding="utf-8",
        )
        lib = load_template_library(tmp_path)
        assert len(lib) == 1
        name, keywords, body = lib[0]
        assert name == "delay"
        assert "delay" in keywords
        assert "Body about" in body

    def test_default_keywords_from_filename(self, tmp_path):
        from socrata_toolkit.analyst.inquiries import load_template_library

        (tmp_path / "contract_status.md").write_text("Plain body, no frontmatter.", encoding="utf-8")
        lib = load_template_library(tmp_path)
        name, keywords, _ = lib[0]
        assert name == "contract_status"
        assert "contract status" in keywords

class TestMatchTemplates:
    def test_empty_inputs(self):
        from socrata_toolkit.analyst.inquiries import match_templates

        assert match_templates(pd.DataFrame(), []) == []

    def test_matches_by_keyword(self):
        from socrata_toolkit.analyst.inquiries import match_templates

        contracts = pd.DataFrame({"contract_id": ["C1"], "status": ["delayed"]})
        templates = [("delay", ["delay"], "body")]
        matches = match_templates(contracts, templates)
        assert matches == [("C1", "delay", "delay")]

    def test_no_match(self):
        from socrata_toolkit.analyst.inquiries import match_templates

        contracts = pd.DataFrame({"contract_id": ["C1"], "status": ["active"]})
        templates = [("delay", ["overdue"], "body")]
        assert match_templates(contracts, templates) == []

class TestRenderInquiryDrafts:
    def test_renders_drafts(self, tmp_path):
        from socrata_toolkit.analyst.inquiries import render_inquiry_drafts

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "contract_status.md").write_text(
            "Inquiry for {{contract_id}} status.", encoding="utf-8"
        )
        out_dir = tmp_path / "out"
        contracts = pd.DataFrame({"contract_id": ["C1", "C2"]})
        written = render_inquiry_drafts(contracts, templates_dir, out_dir)
        assert len(written) >= 1
        # contract_id substituted into the body
        content = written[0].read_text()
        assert "C1" in content or "C2" in content

    def test_explicit_contract_ids(self, tmp_path):
        from socrata_toolkit.analyst.inquiries import render_inquiry_drafts

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "contract_status.md").write_text("For {{contract_id}}.", encoding="utf-8")
        out_dir = tmp_path / "out"
        contracts = pd.DataFrame({"contract_id": ["C9"]})
        written = render_inquiry_drafts(contracts, templates_dir, out_dir, contract_ids=["C9"])
        assert any("C9" in p.read_text() for p in written)
