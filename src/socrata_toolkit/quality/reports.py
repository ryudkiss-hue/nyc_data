"""
Quality Reporting - Report Generation for Data Quality Metrics

Generates comprehensive quality reports in multiple formats (HTML, PDF, JSON).
Includes executive summaries, trend analysis, SLA compliance, and anomalies.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class ReportMetadata:
    """Metadata for a quality report."""
    title: str
    generated_at: datetime
    report_type: str  # 'daily', 'dataset', 'sla', 'anomaly'
    period_start: datetime
    period_end: datetime
    author: str = "Data Quality System"

class QualityReportGenerator:
    """Generates comprehensive quality reports.

    Creates executive summaries, detailed metrics, trend analysis,
    SLA compliance reports, and anomaly detection reports.
    """

    def __init__(self, output_dir: Path | str = "./quality_reports"):
        """Initialize report generator.

        Args:
            output_dir: Directory for saving reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(
        self,
        datasets: dict[str, dict[str, Any]],
        sla_results: dict[str, Any],
        anomalies: list[Any],
    ) -> dict[str, Any]:
        """Generate daily quality report across all datasets.

        Args:
            datasets: Dict of dataset quality summaries
            sla_results: SLA compliance results
            anomalies: List of detected anomalies

        Returns:
            Report dictionary
        """
        report = {
            "title": "Daily Data Quality Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "daily",
            "summary": self._generate_summary(datasets, sla_results),
            "datasets": self._summarize_datasets(datasets),
            "sla_compliance": sla_results,
            "anomalies": [a.to_dict() if hasattr(a, 'to_dict') else a for a in anomalies],
            "recommendations": self._generate_recommendations(datasets, anomalies),
        }
        return report

    def generate_dataset_report(
        self,
        dataset_name: str,
        profile: dict[str, Any] | None = None,
        validation_results: list[dict[str, Any]] | None = None,
        anomalies: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Generate detailed report for a single dataset.

        Args:
            dataset_name: Name of dataset
            profile: Data profile
            validation_results: Validation results
            anomalies: Detected anomalies

        Returns:
            Report dictionary
        """
        report = {
            "title": f"Dataset Quality Report: {dataset_name}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "dataset",
            "dataset_name": dataset_name,
            "profile": profile or {},
            "validation_results": validation_results or [],
            "anomalies": [a.to_dict() if hasattr(a, 'to_dict') else a for a in (anomalies or [])],
            "metrics": self._extract_metrics(profile, validation_results),
        }
        return report

    def generate_sla_compliance_report(
        self,
        sla_evaluations: dict[str, dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Generate SLA compliance report.

        Args:
            sla_evaluations: Dict of SLA names to compliance data
            period_start: Report period start
            period_end: Report period end

        Returns:
            Report dictionary
        """
        compliant = sum(
            1 for e in sla_evaluations.values() if e.get("compliant", False)
        )
        total = len(sla_evaluations)

        report = {
            "title": "SLA Compliance Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "sla",
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "summary": {
                "total_slas": total,
                "compliant": compliant,
                "non_compliant": total - compliant,
                "compliance_rate": compliant / total if total > 0 else 0,
            },
            "sla_details": sla_evaluations,
            "trends": self._analyze_sla_trends(sla_evaluations),
        }
        return report

    def generate_anomaly_report(
        self,
        anomalies: list[Any],
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Generate anomaly detection report.

        Args:
            anomalies: List of anomalies
            period_start: Report period start
            period_end: Report period end

        Returns:
            Report dictionary
        """
        if not anomalies:
            return {
                "title": "Anomaly Report",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_type": "anomaly",
                "anomaly_count": 0,
                "anomalies": [],
                "severity_summary": {},
            }

        # Group by severity
        by_severity = {}
        for anomaly in anomalies:
            anom_dict = anomaly.to_dict() if hasattr(anomaly, 'to_dict') else anomaly
            severity = anom_dict.get("severity", "unknown")
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(anom_dict)

        report = {
            "title": "Anomaly Detection Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "anomaly",
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "summary": {
                "total_anomalies": len(anomalies),
                "by_severity": {s: len(v) for s, v in by_severity.items()},
            },
            "anomalies": [a.to_dict() if hasattr(a, 'to_dict') else a for a in anomalies],
            "severity_breakdown": by_severity,
        }
        return report

    def _generate_summary(
        self,
        datasets: dict[str, dict[str, Any]],
        sla_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate executive summary.

        Args:
            datasets: Dataset quality data
            sla_results: SLA compliance data

        Returns:
            Summary dictionary
        """
        total_datasets = len(datasets)
        healthy_datasets = sum(
            1 for d in datasets.values()
            if d.get("quality_score", 0) > 0.8
        )

        return {
            "total_datasets": total_datasets,
            "healthy_datasets": healthy_datasets,
            "health_percentage": healthy_datasets / total_datasets if total_datasets > 0 else 0,
            "sla_compliance": sla_results.get("overall_compliance", 0),
            "overall_status": "HEALTHY" if healthy_datasets / total_datasets > 0.9 else "DEGRADED",
        }

    def _summarize_datasets(
        self, datasets: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Summarize dataset quality metrics.

        Args:
            datasets: Dataset data

        Returns:
            Summarized data
        """
        return {
            name: {
                "quality_score": data.get("quality_score", 0),
                "row_count": data.get("row_count", 0),
                "validation_status": data.get("validation_status", "unknown"),
                "last_updated": data.get("last_updated", "unknown"),
            }
            for name, data in datasets.items()
        }

    def _extract_metrics(
        self,
        profile: dict[str, Any] | None,
        validation_results: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Extract key metrics from profile and validation.

        Args:
            profile: Data profile
            validation_results: Validation results

        Returns:
            Key metrics
        """
        metrics = {
            "profile_metrics": profile or {},
            "validation_metrics": {},
        }

        if validation_results:
            pass_count = sum(1 for r in validation_results if r.get("passed", False))
            total = len(validation_results)
            metrics["validation_metrics"] = {
                "total_checks": total,
                "passed": pass_count,
                "failed": total - pass_count,
                "pass_rate": pass_count / total if total > 0 else 0,
            }

        return metrics

    def _analyze_sla_trends(
        self, sla_evaluations: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze trends in SLA compliance.

        Args:
            sla_evaluations: SLA evaluation data

        Returns:
            Trend analysis
        """
        improving = sum(
            1 for e in sla_evaluations.values()
            if e.get("trend") == "improving"
        )
        degrading = sum(
            1 for e in sla_evaluations.values()
            if e.get("trend") == "degrading"
        )
        stable = sum(
            1 for e in sla_evaluations.values()
            if e.get("trend") == "stable"
        )

        return {
            "improving_metrics": improving,
            "degrading_metrics": degrading,
            "stable_metrics": stable,
            "overall_trend": "improving" if improving > degrading else ("stable" if improving == degrading else "degrading"),
        }

    def _generate_recommendations(
        self,
        datasets: dict[str, dict[str, Any]],
        anomalies: list[Any],
    ) -> list[str]:
        """Generate recommendations based on quality state.

        Args:
            datasets: Dataset quality data
            anomalies: Detected anomalies

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check for low quality datasets
        low_quality = [
            name for name, data in datasets.items()
            if data.get("quality_score", 0) < 0.8
        ]
        if low_quality:
            recommendations.append(
                f"Investigate quality issues in: {', '.join(low_quality)}"
            )

        # Check for anomalies
        if anomalies:
            critical = sum(
                1 for a in anomalies
                if (a.to_dict() if hasattr(a, 'to_dict') else a).get("severity") == "critical"
            )
            if critical > 0:
                recommendations.append(
                    f"Address {critical} critical anomalies immediately"
                )

        if not recommendations:
            recommendations.append("All quality metrics are healthy")

        return recommendations

    def export_to_json(self, report: dict[str, Any], filename: str) -> Path:
        """Export report to JSON.

        Args:
            report: Report dictionary
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Exported report to {filepath}")
        return filepath

    def export_to_html(self, report: dict[str, Any], filename: str) -> Path:
        """Export report to HTML.

        Args:
            report: Report dictionary
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename

        html = f"""
        <html>
        <head>
            <title>{report.get('title', 'Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f0f0f0; padding: 10px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; }}
                .status-good {{ color: green; }}
                .status-bad {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            </style>
        </head>
        <body>
            <h1>{report.get('title', 'Report')}</h1>
            <p>Generated: {report.get('generated_at', 'Unknown')}</p>

            <div class="summary">
                <h2>Summary</h2>
                {self._html_dict(report.get('summary', {}))}
            </div>

            <h2>Details</h2>
            {self._html_dict({k: v for k, v in report.items() if k not in ['title', 'generated_at', 'summary']})}
        </body>
        </html>
        """

        with open(filepath, 'w') as f:
            f.write(html)
        logger.info(f"Exported HTML report to {filepath}")
        return filepath

    def _html_dict(self, data: dict[str, Any]) -> str:
        """Convert dictionary to HTML table.

        Args:
            data: Dictionary

        Returns:
            HTML string
        """
        if not data:
            return "<p>No data</p>"

        html = "<table><tr>"
        for key in data.keys():
            html += f"<th>{key}</th>"
        html += "</tr>"

        for value_list in zip(*data.values()):
            html += "<tr>"
            for val in value_list:
                html += f"<td>{val}</td>"
            html += "</tr>"

        html += "</table>"
        return html

    def export_to_csv(self, report: dict[str, Any], filename: str) -> Path:
        """Export report data to CSV.

        Args:
            report: Report dictionary
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename

        # Convert report to CSV-friendly format
        data_list = []

        if "anomalies" in report and isinstance(report["anomalies"], list):
            data_list = report["anomalies"]
        elif "sla_details" in report:
            data_list = [{"sla": k, **v} for k, v in report["sla_details"].items()]
        elif "datasets" in report:
            data_list = [{"dataset": k, **v} for k, v in report["datasets"].items()]

        if data_list:
            df = pd.DataFrame(data_list)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported CSV report to {filepath}")

        return filepath
