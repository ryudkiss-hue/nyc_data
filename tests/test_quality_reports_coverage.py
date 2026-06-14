"""Tests for quality.reports module - Quality report generation."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from socrata_toolkit.quality.reports import QualityReportGenerator, ReportMetadata


class TestReportMetadata:
    """Tests for ReportMetadata dataclass."""

    def test_report_metadata_creation(self):
        """Test creating ReportMetadata."""
        now = datetime.now(timezone.utc)
        metadata = ReportMetadata(
            title="Daily Report",
            generated_at=now,
            report_type="daily",
            period_start=now - timedelta(days=1),
            period_end=now,
            author="Test Author",
        )
        assert metadata.title == "Daily Report"
        assert metadata.report_type == "daily"
        assert metadata.author == "Test Author"

    def test_report_metadata_default_author(self):
        """Test ReportMetadata with default author."""
        now = datetime.now(timezone.utc)
        metadata = ReportMetadata(
            title="Test",
            generated_at=now,
            report_type="daily",
            period_start=now,
            period_end=now,
        )
        assert metadata.author == "Data Quality System"

class TestQualityReportGenerator:
    """Tests for QualityReportGenerator class."""

    def test_generator_initialization(self):
        """Test initializing QualityReportGenerator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            assert gen.output_dir == Path(tmpdir)
            assert gen.output_dir.exists()

    def test_generate_daily_report_basic(self):
        """Test generating a daily report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {
                "dataset1": {"quality_score": 0.85, "row_count": 1000},
                "dataset2": {"quality_score": 0.75, "row_count": 500},
            }
            sla_results = {"overall_compliance": 0.95}
            anomalies = []

            report = gen.generate_daily_report(datasets, sla_results, anomalies)

            assert report["title"] == "Daily Data Quality Report"
            assert report["report_type"] == "daily"
            assert "summary" in report
            assert "datasets" in report
            assert "sla_compliance" in report

    def test_generate_daily_report_with_anomalies(self):
        """Test daily report with anomalies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {"dataset1": {"quality_score": 0.85}}
            sla_results = {"overall_compliance": 0.95}
            anomalies = [{"type": "outlier", "severity": "high"}]

            report = gen.generate_daily_report(datasets, sla_results, anomalies)

            assert len(report["anomalies"]) == 1
            assert "recommendations" in report

    def test_generate_dataset_report(self):
        """Test generating a dataset-specific report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            profile = {"row_count": 1000, "column_count": 10}
            validation_results = [
                {"check": "not_null", "passed": True},
                {"check": "unique", "passed": False},
            ]

            report = gen.generate_dataset_report(
                "test_dataset",
                profile=profile,
                validation_results=validation_results,
            )

            assert report["title"] == "Dataset Quality Report: test_dataset"
            assert report["report_type"] == "dataset"
            assert report["dataset_name"] == "test_dataset"
            assert "metrics" in report

    def test_generate_dataset_report_without_optional_fields(self):
        """Test dataset report without optional profile/results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = gen.generate_dataset_report("dataset_only")

            assert report["dataset_name"] == "dataset_only"
            assert report["profile"] == {}
            assert report["validation_results"] == []
            assert report["anomalies"] == []

    def test_generate_sla_compliance_report(self):
        """Test generating SLA compliance report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            now = datetime.now(timezone.utc)
            sla_evaluations = {
                "freshness": {"compliant": True, "value": 98},
                "availability": {"compliant": True, "value": 99},
                "accuracy": {"compliant": False, "value": 70},
            }

            report = gen.generate_sla_compliance_report(
                sla_evaluations,
                period_start=now - timedelta(days=30),
                period_end=now,
            )

            assert report["title"] == "SLA Compliance Report"
            assert report["report_type"] == "sla"
            assert report["summary"]["total_slas"] == 3
            assert report["summary"]["compliant"] == 2
            assert report["summary"]["non_compliant"] == 1

    def test_generate_sla_compliance_rate(self):
        """Test SLA compliance rate calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            now = datetime.now(timezone.utc)
            sla_evaluations = {
                "sla1": {"compliant": True},
                "sla2": {"compliant": True},
                "sla3": {"compliant": False},
                "sla4": {"compliant": False},
            }

            report = gen.generate_sla_compliance_report(
                sla_evaluations, now - timedelta(days=1), now
            )

            assert report["summary"]["compliance_rate"] == 0.5

    def test_generate_anomaly_report_empty(self):
        """Test anomaly report with no anomalies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            now = datetime.now(timezone.utc)

            report = gen.generate_anomaly_report(
                [],
                period_start=now - timedelta(days=1),
                period_end=now,
            )

            assert report["anomaly_count"] == 0
            assert report["anomalies"] == []
            assert report["severity_summary"] == {}

    def test_generate_anomaly_report_with_anomalies(self):
        """Test anomaly report with anomalies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            now = datetime.now(timezone.utc)
            anomalies = [
                {"type": "outlier", "severity": "high"},
                {"type": "duplicate", "severity": "medium"},
                {"type": "missing", "severity": "high"},
            ]

            report = gen.generate_anomaly_report(
                anomalies,
                period_start=now - timedelta(days=1),
                period_end=now,
            )

            assert report["title"] == "Anomaly Detection Report"
            assert report["report_type"] == "anomaly"
            assert report["summary"]["total_anomalies"] == 3
            assert "severity_breakdown" in report

    def test_generate_summary(self):
        """Test executive summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {
                "ds1": {"quality_score": 0.9},  # Healthy
                "ds2": {"quality_score": 0.85},  # Healthy
                "ds3": {"quality_score": 0.75},  # Not healthy
            }
            sla_results = {"overall_compliance": 0.95}

            summary = gen._generate_summary(datasets, sla_results)

            assert summary["total_datasets"] == 3
            assert summary["healthy_datasets"] == 2
            assert summary["sla_compliance"] == 0.95

    def test_generate_recommendations_low_quality(self):
        """Test recommendations for low quality datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {
                "bad_ds": {"quality_score": 0.7},
                "good_ds": {"quality_score": 0.9},
            }
            anomalies = []

            recommendations = gen._generate_recommendations(datasets, anomalies)

            assert any("bad_ds" in r for r in recommendations)

    def test_generate_recommendations_critical_anomalies(self):
        """Test recommendations for critical anomalies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {"ds1": {"quality_score": 0.9}}
            anomalies = [
                {"severity": "critical"},
                {"severity": "critical"},
                {"severity": "warning"},
            ]

            recommendations = gen._generate_recommendations(datasets, anomalies)

            assert any("2 critical anomalies" in r for r in recommendations)

    def test_export_to_json(self):
        """Test exporting report to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = {
                "title": "Test Report",
                "data": {"key": "value"},
            }

            filepath = gen.export_to_json(report, "test_report.json")

            assert filepath.exists()
            with open(filepath) as f:
                loaded = json.load(f)
            assert loaded["title"] == "Test Report"

    def test_export_to_html(self):
        """Test exporting report to HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = {
                "title": "Test Report",
                "generated_at": "2023-01-01",
                "summary": {"health": "good"},
            }

            filepath = gen.export_to_html(report, "test_report.html")

            assert filepath.exists()
            content = filepath.read_text()
            assert "Test Report" in content
            assert "<html>" in content

    def test_export_to_csv_from_anomalies(self):
        """Test exporting anomaly data to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = {
                "anomalies": [
                    {"type": "outlier", "severity": "high"},
                    {"type": "duplicate", "severity": "medium"},
                ]
            }

            filepath = gen.export_to_csv(report, "anomalies.csv")

            assert filepath.exists()
            df = pd.read_csv(filepath)
            assert len(df) == 2
            assert "type" in df.columns

    def test_export_to_csv_from_sla_details(self):
        """Test exporting SLA data to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = {
                "sla_details": {
                    "freshness": {"compliant": True, "value": 99},
                    "availability": {"compliant": False, "value": 95},
                }
            }

            filepath = gen.export_to_csv(report, "sla.csv")

            assert filepath.exists()
            df = pd.read_csv(filepath)
            assert len(df) == 2
            assert "sla" in df.columns

    def test_export_to_csv_from_datasets(self):
        """Test exporting dataset data to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            report = {
                "datasets": {
                    "ds1": {"quality_score": 0.9, "row_count": 1000},
                    "ds2": {"quality_score": 0.8, "row_count": 500},
                }
            }

            filepath = gen.export_to_csv(report, "datasets.csv")

            assert filepath.exists()
            df = pd.read_csv(filepath)
            assert len(df) == 2
            assert "dataset" in df.columns

    def test_extract_metrics_with_profile_and_validation(self):
        """Test extracting metrics from profile and validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            profile = {"row_count": 1000}
            validation_results = [
                {"passed": True},
                {"passed": True},
                {"passed": False},
            ]

            metrics = gen._extract_metrics(profile, validation_results)

            assert metrics["validation_metrics"]["total_checks"] == 3
            assert metrics["validation_metrics"]["passed"] == 2
            assert metrics["validation_metrics"]["failed"] == 1
            assert metrics["validation_metrics"]["pass_rate"] == 2 / 3

    def test_analyze_sla_trends(self):
        """Test SLA trend analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            sla_evaluations = {
                "sla1": {"trend": "improving"},
                "sla2": {"trend": "improving"},
                "sla3": {"trend": "degrading"},
                "sla4": {"trend": "stable"},
            }

            trends = gen._analyze_sla_trends(sla_evaluations)

            assert trends["improving_metrics"] == 2
            assert trends["degrading_metrics"] == 1
            assert trends["stable_metrics"] == 1

    def test_summarize_datasets(self):
        """Test dataset summarization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            datasets = {
                "ds1": {
                    "quality_score": 0.9,
                    "row_count": 1000,
                    "validation_status": "pass",
                    "last_updated": "2023-01-01",
                },
                "ds2": {"quality_score": 0.7},
            }

            summary = gen._summarize_datasets(datasets)

            assert "ds1" in summary
            assert summary["ds1"]["quality_score"] == 0.9
            assert summary["ds2"]["quality_score"] == 0.7
            assert summary["ds2"]["row_count"] == 0  # Default value

    def test_html_dict_conversion(self):
        """Test dictionary to HTML table conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            data = {"col1": [1, 2], "col2": [3, 4]}

            html = gen._html_dict(data)

            assert "<table>" in html
            assert "<th>col1</th>" in html
            assert "<th>col2</th>" in html

    def test_html_dict_empty(self):
        """Test HTML conversion with empty dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = QualityReportGenerator(output_dir=tmpdir)
            html = gen._html_dict({})
            assert "No data" in html
