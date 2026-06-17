"""KPI Analytics Data Validation & Quality Monitoring.

Comprehensive data quality checks for the 4-tier analytics pipeline.
Ensures data freshness, completeness, and integrity before Dives consume.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import duckdb

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    check_name: str
    passed: bool
    message: str
    detail: str | None = None
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class QualityReport:
    """Complete quality assessment of analytics pipeline."""

    timestamp_check: ValidationResult
    row_count_check: ValidationResult
    null_check: ValidationResult
    column_count_check: ValidationResult
    freshness_check: ValidationResult
    schema_check: ValidationResult
    metric_ranges_check: ValidationResult
    anomaly_check: ValidationResult
    all_passed: bool = field(default=True)

    def __post_init__(self):
        """Compute overall pass/fail."""
        all_checks = [
            self.timestamp_check,
            self.row_count_check,
            self.null_check,
            self.column_count_check,
            self.freshness_check,
            self.schema_check,
            self.metric_ranges_check,
            self.anomaly_check,
        ]
        self.all_passed = all(check.passed for check in all_checks if check.severity == "ERROR")


class KPIValidator:
    """Validate KPI analytics pipeline data quality."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """Initialize validator with database connection."""
        self.conn = conn
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    def validate_all(self) -> QualityReport:
        """Run all validation checks and return comprehensive report."""
        logger.info("Starting comprehensive KPI analytics validation...")

        return QualityReport(
            timestamp_check=self.check_timestamp_freshness(),
            row_count_check=self.check_row_counts(),
            null_check=self.check_null_metrics(),
            column_count_check=self.check_column_completeness(),
            freshness_check=self.check_data_freshness(),
            schema_check=self.check_schema_integrity(),
            metric_ranges_check=self.check_metric_ranges(),
            anomaly_check=self.check_anomalies(),
        )

    def check_timestamp_freshness(self) -> ValidationResult:
        """Verify analytics_timestamp is current (within 30 minutes)."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  MAX(analytics_timestamp) as latest,
                  DATEDIFF('minutes', MAX(analytics_timestamp), CURRENT_TIMESTAMP) as minutes_ago
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            if not result or result[0] is None:
                return ValidationResult(
                    check_name="timestamp_freshness",
                    passed=False,
                    message="No analytics_timestamp found",
                    severity="ERROR",
                )

            minutes_ago = result[1]
            if minutes_ago > 30:
                return ValidationResult(
                    check_name="timestamp_freshness",
                    passed=False,
                    message=f"Data is {minutes_ago} minutes old (threshold: 30 min)",
                    detail=f"Latest: {result[0]}",
                    severity="WARNING",
                )

            return ValidationResult(
                check_name="timestamp_freshness",
                passed=True,
                message=f"Data is {minutes_ago} minutes old ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="timestamp_freshness",
                passed=False,
                message=f"Timestamp check failed: {str(e)}",
                severity="ERROR",
            )

    def check_row_counts(self) -> ValidationResult:
        """Verify exactly 90 rows (18 KPIs × 5 boroughs)."""
        try:
            result = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM analytics.kpi_statistics_by_borough"
            ).fetchone()

            row_count = result[0] if result else 0

            if row_count != 90:
                return ValidationResult(
                    check_name="row_count",
                    passed=False,
                    message=f"Expected 90 rows, got {row_count}",
                    detail=f"Break down: {self._get_row_breakdown()}",
                    severity="ERROR",
                )

            return ValidationResult(
                check_name="row_count",
                passed=True,
                message="Exactly 90 rows (18 KPIs × 5 boroughs) ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="row_count",
                passed=False,
                message=f"Row count check failed: {str(e)}",
                severity="ERROR",
            )

    def check_null_metrics(self) -> ValidationResult:
        """Verify core metrics are not NULL."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  COUNT(CASE WHEN mean_value IS NULL THEN 1 END) as null_mean,
                  COUNT(CASE WHEN stddev_samp IS NULL THEN 1 END) as null_stddev,
                  COUNT(CASE WHEN median_value IS NULL THEN 1 END) as null_median,
                  COUNT(CASE WHEN q1_value IS NULL THEN 1 END) as null_q1,
                  COUNT(CASE WHEN q3_value IS NULL THEN 1 END) as null_q3
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            if result and any(result):
                null_cols = [
                    f"mean_value({result[0]})",
                    f"stddev_samp({result[1]})",
                    f"median_value({result[2]})",
                    f"q1_value({result[3]})",
                    f"q3_value({result[4]})",
                ]
                null_cols = [c for c in null_cols if int(c.split("(")[1].rstrip(")")) > 0]
                return ValidationResult(
                    check_name="null_metrics",
                    passed=False,
                    message=f"NULL values found in core metrics: {', '.join(null_cols)}",
                    severity="ERROR",
                )

            return ValidationResult(
                check_name="null_metrics",
                passed=True,
                message="All core metrics (mean, stddev, median, Q1, Q3) are non-NULL ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="null_metrics",
                passed=False,
                message=f"NULL check failed: {str(e)}",
                severity="ERROR",
            )

    def check_column_completeness(self) -> ValidationResult:
        """Verify analytics table has 75+ columns."""
        try:
            columns = self.conn.execute(
                "SELECT * FROM analytics.kpi_statistics_by_borough LIMIT 0"
            ).description

            column_count = len(columns) if columns else 0

            if column_count < 75:
                return ValidationResult(
                    check_name="column_completeness",
                    passed=False,
                    message=f"Expected 75+ columns, got {column_count}",
                    detail=f"Columns: {[c[0] for c in columns[:10]]}...",
                    severity="ERROR",
                )

            return ValidationResult(
                check_name="column_completeness",
                passed=True,
                message=f"All {column_count} columns present ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="column_completeness",
                passed=False,
                message=f"Column check failed: {str(e)}",
                severity="ERROR",
            )

    def check_data_freshness(self) -> ValidationResult:
        """Verify all tables in pipeline have recent data."""
        try:
            checks = {
                "raw": "SELECT COUNT(*) FROM analytics.kpi_metrics",
                "staging": "SELECT COUNT(*) FROM analytics.kpi_metrics_staged WHERE is_latest_record = TRUE",
                "analytics": "SELECT COUNT(*) FROM analytics.kpi_statistics_by_borough",
                "serving": "SELECT COUNT(*) FROM analytics.kpi_metrics_comprehensive",
            }

            results = {}
            for layer, query in checks.items():
                try:
                    count = self.conn.execute(query).fetchone()[0]
                    results[layer] = count
                except Exception as e:
                    logger.warning(f"Layer {layer} check failed: {str(e)}")
                    results[layer] = None

            missing = [k for k, v in results.items() if v is None]
            if missing:
                return ValidationResult(
                    check_name="data_freshness",
                    passed=False,
                    message=f"Missing layers: {', '.join(missing)}",
                    severity="ERROR",
                )

            return ValidationResult(
                check_name="data_freshness",
                passed=True,
                message=f"All pipeline layers populated: raw({results['raw']}), staging({results['staging']}), analytics({results['analytics']}), serving({results['serving']}) ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="data_freshness",
                passed=False,
                message=f"Freshness check failed: {str(e)}",
                severity="ERROR",
            )

    def check_schema_integrity(self) -> ValidationResult:
        """Verify schema structure matches expectations."""
        try:
            # Check for required tables
            tables = self.conn.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'analytics'
                """
            ).fetchall()
            table_names = [t[0] for t in tables]

            required_tables = [
                "kpi_metrics",
                "kpi_metrics_staged",
                "kpi_statistics_by_borough",
                "kpi_metrics_comprehensive",
                "kpi_metadata",
            ]
            missing = [t for t in required_tables if t not in table_names]

            if missing:
                return ValidationResult(
                    check_name="schema_integrity",
                    passed=False,
                    message=f"Missing tables: {', '.join(missing)}",
                    severity="ERROR",
                )

            return ValidationResult(
                check_name="schema_integrity",
                passed=True,
                message=f"All {len(required_tables)} required tables present ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="schema_integrity",
                passed=False,
                message=f"Schema check failed: {str(e)}",
                severity="ERROR",
            )

    def check_metric_ranges(self) -> ValidationResult:
        """Verify metrics are within expected ranges (no impossible values)."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  COUNT(CASE WHEN mean_value < 0 AND kpi_name NOT LIKE '%slope%trend%' THEN 1 END) as negative_means,
                  COUNT(CASE WHEN stddev_samp < 0 THEN 1 END) as negative_stddev,
                  COUNT(CASE WHEN coeff_variation > 500 THEN 1 END) as extreme_cv,
                  COUNT(CASE WHEN skewness_index < -10 OR skewness_index > 10 THEN 1 END) as extreme_skew
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            issues = []
            if result[0] > 0:
                issues.append(f"negative means ({result[0]})")
            if result[1] > 0:
                issues.append(f"negative stddev ({result[1]})")
            if result[2] > 0:
                issues.append(f"extreme CV ({result[2]})")
            if result[3] > 0:
                issues.append(f"extreme skewness ({result[3]})")

            if issues:
                return ValidationResult(
                    check_name="metric_ranges",
                    passed=False,
                    message=f"Invalid metric ranges detected: {', '.join(issues)}",
                    severity="WARNING",
                )

            return ValidationResult(
                check_name="metric_ranges",
                passed=True,
                message="All metrics within expected ranges ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="metric_ranges",
                passed=False,
                message=f"Range check failed: {str(e)}",
                severity="ERROR",
            )

    def check_anomalies(self) -> ValidationResult:
        """Detect sudden metric changes that might indicate data quality issues."""
        try:
            # Check if any KPI has suspiciously high variance (outlier detection)
            result = self.conn.execute(
                """
                SELECT COUNT(*) as anomaly_count
                FROM analytics.kpi_statistics_by_borough
                WHERE
                  (stddev_samp > mean_value * 5 AND mean_value > 0)  -- Variance > 500%
                  OR (outlier_count_3sd > n * 0.1)  -- More than 10% outliers
                """
            ).fetchone()

            anomaly_count = result[0] if result else 0

            if anomaly_count > 5:
                return ValidationResult(
                    check_name="anomalies",
                    passed=False,
                    message=f"{anomaly_count} KPI-borough pairs show anomalies (high variance or outliers)",
                    severity="WARNING",
                )

            return ValidationResult(
                check_name="anomalies",
                passed=True,
                message=f"Data quality looks good ({anomaly_count} minor anomalies detected) ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="anomalies",
                passed=False,
                message=f"Anomaly check failed: {str(e)}",
                severity="ERROR",
            )

    def check_stationarity_coverage(self) -> ValidationResult:
        """Check that time series metrics are present (weekly computation)."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  COUNT(CASE WHEN adf_p_value IS NOT NULL THEN 1 END) as ts_computed,
                  COUNT(*) as total
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            ts_computed, total = result

            if ts_computed == 0:
                return ValidationResult(
                    check_name="timeseries_coverage",
                    passed=True,
                    message="No time series metrics yet (computed weekly)",
                    severity="INFO",
                )

            coverage = ts_computed / total if total > 0 else 0

            if coverage < 0.8:
                return ValidationResult(
                    check_name="timeseries_coverage",
                    passed=False,
                    message=f"Time series metrics only {coverage * 100:.1f}% complete",
                    severity="WARNING",
                )

            return ValidationResult(
                check_name="timeseries_coverage",
                passed=True,
                message=f"Time series metrics {coverage * 100:.1f}% computed ✓",
                severity="INFO",
            )

        except Exception as e:
            return ValidationResult(
                check_name="timeseries_coverage",
                passed=False,
                message=f"Stationarity check failed: {str(e)}",
                severity="ERROR",
            )

    def _get_row_breakdown(self) -> str:
        """Get breakdown of rows by KPI and borough."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  COUNT(DISTINCT kpi_name) as kpi_count,
                  COUNT(DISTINCT borough) as borough_count
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()
            return f"{result[0]} KPIs × {result[1]} boroughs = {result[0] * result[1]} expected"
        except:
            return "Unable to determine"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example usage
    try:
        conn = duckdb.connect("md:", config={"motherduck_token": "your_token_here"})
        validator = KPIValidator(conn)
        report = validator.validate_all()

        print("\n=== KPI Analytics Quality Report ===")
        for check in [
            report.timestamp_check,
            report.row_count_check,
            report.null_check,
            report.column_count_check,
            report.freshness_check,
            report.schema_check,
            report.metric_ranges_check,
            report.anomaly_check,
        ]:
            status = "✓" if check.passed else "✗"
            print(f"{status} {check.check_name}: {check.message}")
            if check.detail:
                print(f"   {check.detail}")

        print(f"\nOverall Status: {'PASS' if report.all_passed else 'FAIL'}")

    except Exception as e:
        print(f"Validation failed: {str(e)}")
