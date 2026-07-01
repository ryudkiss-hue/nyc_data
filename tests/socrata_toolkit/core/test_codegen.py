"""Unit tests for the socrata_toolkit.codegen package.

Tests RegistryLoader validation, each generator's code-generation output,
and the CodegenFramework orchestrator — all using a minimal in-memory
registry so no real YAML file or filesystem writes are required during
the core unit tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from socrata_toolkit.codegen import (
    CallbackGenerator,
    ChartGenerator,
    CodegenFramework,
    DocsGenerator,
    KPIGenerator,
    LayoutGenerator,
    RegistryLoader,
)

# ---------------------------------------------------------------------------
# Minimal in-memory registry fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_registry(tmp_path):
    """Minimal valid DATASET_REGISTRY.yaml written to a temp file."""
    reg = {
        "registry_metadata": {
            "version": "1.0",
            "total_datasets": 2,
            "domain": "data.cityofnewyork.us",
        },
        "datasets": {
            "inspection": {
                "fourfour": "dntt-gqwq",
                "name": "Sidewalk Inspections",
                "status": "active",
                "kpis": ["inspections_scheduled_week", "inspection_completion_rate"],
                "tags": ["core", "daily"],
                "visualization": {
                    "default_chart": "vertical_bar",
                    "iv_column": "borough",
                    "dv_column": "violation_count",
                    "aggregation": "sum",
                    "title": "Weekly Inspections by Borough",
                    "suggested_iv": "Borough",
                    "suggested_dv": "Count",
                    "suggested_date": "Inspection Date",
                    "has_geographic_data": False,
                },
            },
            "violations": {
                "fourfour": "wqe2-rbyg",
                "name": "Sidewalk Violations",
                "status": "active",
                "kpis": ["open_violations_count"],
                "tags": ["core"],
                "visualization": {
                    "default_chart": "horizontal_bar",
                    "iv_column": "borough",
                    "dv_column": "count",
                    "aggregation": "count",
                    "title": "Open Violations by Borough",
                    "suggested_iv": "Borough",
                    "suggested_dv": "Violations",
                    "suggested_date": "Created Date",
                    "has_geographic_data": False,
                },
            },
        },
        "defaults": {
            "chart_height": 400,
            "color_palette": ["#1f77b4", "#ff7f0e"],
        },
        "generators": {
            "output_paths": {
                "charts": str(tmp_path / "generated" / "plotly_charts.py"),
                "callbacks": str(tmp_path / "generated" / "visualization_callbacks.py"),
                "layout": str(tmp_path / "generated" / "dashboard_layout.py"),
                "kpis": str(tmp_path / "generated" / "kpi_stubs.py"),
                "docs": str(tmp_path / "generated" / "DATASETS.md"),
            }
        },
    }
    reg_path = tmp_path / "DATASET_REGISTRY.yaml"
    reg_path.write_text(yaml.dump(reg))
    return reg, reg_path


# ---------------------------------------------------------------------------
# RegistryLoader tests
# ---------------------------------------------------------------------------

class TestRegistryLoader:
    def test_loads_valid_yaml(self, minimal_registry):
        reg_dict, reg_path = minimal_registry
        loader = RegistryLoader(str(reg_path))
        result = loader.load()
        assert result["registry_metadata"]["total_datasets"] == 2
        assert "inspection" in result["datasets"]

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            RegistryLoader(str(tmp_path / "nonexistent.yaml"))

    def test_raises_on_missing_required_section(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("registry_metadata:\n  version: '1.0'\n  total_datasets: 0\n  domain: x\n")
        loader = RegistryLoader(str(bad))
        with pytest.raises(KeyError, match="datasets"):
            loader.load()

    def test_raises_on_missing_dataset_fourfour(self, tmp_path):
        bad_reg = {
            "registry_metadata": {"version": "1.0", "total_datasets": 1, "domain": "x"},
            "datasets": {"broken": {"name": "X", "status": "active"}},  # no fourfour
            "defaults": {},
            "generators": {"output_paths": {}},
        }
        p = tmp_path / "bad2.yaml"
        p.write_text(yaml.dump(bad_reg))
        loader = RegistryLoader(str(p))
        with pytest.raises(KeyError, match="fourfour"):
            loader.load()

    def test_get_active_datasets_filters_inactive(self, minimal_registry):
        reg_dict, reg_path = minimal_registry
        # Add an inactive dataset
        reg_dict["datasets"]["archived"] = {
            "fourfour": "xxxx-xxxx", "name": "Old", "status": "inactive"
        }
        loader = RegistryLoader(str(reg_path))
        active = loader.get_active_datasets(reg_dict)
        assert "archived" not in active
        assert "inspection" in active

    def test_get_datasets_by_tag(self, minimal_registry):
        reg_dict, _ = minimal_registry
        loader = RegistryLoader.__new__(RegistryLoader)
        daily = loader.get_datasets_by_tag(reg_dict, "daily")
        assert "inspection" in daily
        assert "violations" not in daily

    def test_get_dataset_by_fourfour_found(self, minimal_registry):
        reg_dict, _ = minimal_registry
        loader = RegistryLoader.__new__(RegistryLoader)
        key, ds = loader.get_dataset_by_fourfour(reg_dict, "dntt-gqwq")
        assert key == "inspection"
        assert ds["name"] == "Sidewalk Inspections"

    def test_get_dataset_by_fourfour_not_found(self, minimal_registry):
        reg_dict, _ = minimal_registry
        loader = RegistryLoader.__new__(RegistryLoader)
        result = loader.get_dataset_by_fourfour(reg_dict, "zzzz-zzzz")
        assert result is None


# ---------------------------------------------------------------------------
# ChartGenerator tests
# ---------------------------------------------------------------------------

class TestChartGenerator:
    def test_generate_creates_file(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = ChartGenerator(reg_dict)
        output = gen.generate()
        assert Path(output).exists()

    def test_generated_file_is_valid_python(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = ChartGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        compile(source, output, "exec")  # raises SyntaxError if invalid

    def test_generated_file_contains_class(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = ChartGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "ChartFactory" in source

    def test_generates_entry_per_dataset(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = ChartGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "inspection" in source
        assert "violations" in source


# ---------------------------------------------------------------------------
# CallbackGenerator tests
# ---------------------------------------------------------------------------

class TestCallbackGenerator:
    def test_generate_creates_file(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = CallbackGenerator(reg_dict)
        output = gen.generate()
        assert Path(output).exists()

    def test_generated_file_is_valid_python(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = CallbackGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        compile(source, output, "exec")

    def test_generated_file_contains_callback_factory(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = CallbackGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "CallbackFactory" in source

    def test_generates_entry_per_dataset(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = CallbackGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "inspection" in source
        assert "violations" in source


# ---------------------------------------------------------------------------
# KPIGenerator tests
# ---------------------------------------------------------------------------

class TestKPIGenerator:
    def test_generate_creates_file(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = KPIGenerator(reg_dict)
        output = gen.generate()
        assert Path(output).exists()

    def test_generated_file_is_valid_python(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = KPIGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        compile(source, output, "exec")

    def test_generated_file_contains_kpi_engine(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = KPIGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "KPIEngine" in source

    def test_generates_stub_per_kpi(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = KPIGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        # All 3 unique KPIs across the 2 datasets
        assert "compute_inspections_scheduled_week" in source
        assert "compute_inspection_completion_rate" in source
        assert "compute_open_violations_count" in source

    def test_deduplicates_shared_kpis(self, minimal_registry):
        """KPI shared by two datasets must generate only one stub."""
        reg_dict, _ = minimal_registry
        # Add shared KPI to both datasets
        reg_dict["datasets"]["inspection"]["kpis"].append("shared_kpi")
        reg_dict["datasets"]["violations"]["kpis"].append("shared_kpi")
        gen = KPIGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert source.count("compute_shared_kpi") == 1


# ---------------------------------------------------------------------------
# LayoutGenerator tests
# ---------------------------------------------------------------------------

class TestLayoutGenerator:
    def test_generate_creates_file(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = LayoutGenerator(reg_dict)
        output = gen.generate()
        assert Path(output).exists()

    def test_generated_file_is_valid_python(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = LayoutGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        compile(source, output, "exec")

    def test_generates_entry_per_dataset(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = LayoutGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "inspection" in source
        assert "violations" in source


# ---------------------------------------------------------------------------
# DocsGenerator tests
# ---------------------------------------------------------------------------

class TestDocsGenerator:
    def test_generate_creates_file(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = DocsGenerator(reg_dict)
        output = gen.generate()
        assert Path(output).exists()

    def test_generated_markdown_mentions_datasets(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = DocsGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "Sidewalk Inspections" in source or "inspection" in source
        assert "Sidewalk Violations" in source or "violations" in source

    def test_generated_markdown_mentions_fourfours(self, minimal_registry):
        reg_dict, _ = minimal_registry
        gen = DocsGenerator(reg_dict)
        output = gen.generate()
        source = Path(output).read_text()
        assert "dntt-gqwq" in source
        assert "wqe2-rbyg" in source


# ---------------------------------------------------------------------------
# CodegenFramework orchestrator tests
# ---------------------------------------------------------------------------

class TestCodegenFramework:
    def test_init_loads_registry(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        assert "inspection" in fw.registry["datasets"]

    def test_generate_all_returns_five_paths(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        result = fw.generate_all()
        assert set(result.keys()) == {"charts", "callbacks", "layout", "kpis", "docs"}

    def test_generate_all_files_exist(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        result = fw.generate_all()
        for artifact, path in result.items():
            assert Path(path).exists(), f"{artifact} output file not found at {path}"

    def test_generate_charts_returns_path(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        path = fw.generate_charts()
        assert Path(path).exists()

    def test_generate_callbacks_returns_path(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        path = fw.generate_callbacks()
        assert Path(path).exists()

    def test_generate_kpis_returns_path(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        path = fw.generate_kpis()
        assert Path(path).exists()

    def test_generate_layout_returns_path(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        path = fw.generate_layout()
        assert Path(path).exists()

    def test_generate_docs_returns_path(self, minimal_registry):
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        path = fw.generate_docs()
        assert Path(path).exists()

    def test_idempotent_second_run_overwrites(self, minimal_registry):
        """Running generate_all twice must not fail (idempotent)."""
        _, reg_path = minimal_registry
        fw = CodegenFramework(str(reg_path))
        result1 = fw.generate_all()
        fw2 = CodegenFramework(str(reg_path))
        result2 = fw2.generate_all()
        assert set(result1.keys()) == set(result2.keys())
