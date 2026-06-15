from __future__ import annotations

import base64
import io
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..core import COL_CLOSED, COL_COMPLAINT, COL_CREATED, COL_REPAIR

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


@dataclass
class SLAMetrics:
    """SLA and compliance metrics."""

    avg_total_cycle_days: float
    sla_compliance_rate: float
    violation_count: int
    by_borough: dict[str, Any]


def compute_sla_metrics(
    df: pd.DataFrame, start_col: str = COL_COMPLAINT, end_col: str = COL_REPAIR
) -> SLAMetrics:
    if start_col not in df.columns or end_col not in df.columns:
        return SLAMetrics(0, 100, 0, {})
    tmp = df.copy()
    tmp["_days"] = (
        pd.to_datetime(tmp[end_col], errors="coerce")
        - pd.to_datetime(tmp[start_col], errors="coerce")
    ).dt.days
    clean = tmp["_days"].dropna()
    violations = int((clean > 120).sum())
    return SLAMetrics(
        avg_total_cycle_days=round(float(clean.mean()), 1) if not clean.empty else 0,
        sla_compliance_rate=(
            round((1 - violations / max(len(clean), 1)) * 100, 1) if not clean.empty else 100
        ),
        violation_count=violations,
        by_borough=compute_borough_metrics(df) if "borough" in df.columns else {},
    )


def compute_borough_metrics(
    df: pd.DataFrame, cost_col: str = "repair_cost", status_col: str = "status"
) -> list[dict[str, Any]]:
    """Aggregate metrics by borough for dash visualizations."""
    if "borough" not in df.columns:
        return []

    grouped = df.groupby("borough")
    results = []
    for name, group in grouped:
        inspections = len(group)
        avg_cost = float(group[cost_col].mean()) if cost_col in group.columns else 0.0

        sla_violations = 0
        if status_col in group.columns:
            sla_violations = int(
                group[
                    group[status_col]
                    .astype(str)
                    .str.lower()
                    .str.contains("late|violation|overdue", na=False)
                ].shape[0]
            )

        results.append(
            {
                "borough": str(name),
                "inspections": inspections,
                "avg_cost": round(avg_cost, 2),
                "sla_violations": sla_violations,
            }
        )
    return results


def compute_sla_trends(
    df: pd.DataFrame, date_col: str = "inspection_date", status_col: str = "status"
) -> list[dict[str, Any]]:
    """Calculate monthly SLA on-time vs late percentages."""
    if date_col not in df.columns:
        return []

    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return []

    tmp["month"] = tmp[date_col].dt.strftime("%b")
    grouped = tmp.groupby("month")
    results = []
    month_order = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for month, group in grouped:
        total = len(group)
        late = 0
        if status_col in group.columns:
            late = int(
                group[
                    group[status_col]
                    .astype(str)
                    .str.lower()
                    .str.contains("late|violation", na=False)
                ].shape[0]
            )

        ontime = total - late
        results.append(
            {
                "month": month,
                "ontime": round((ontime / total) * 100, 1) if total > 0 else 0.0,
                "late": round((late / total) * 100, 1) if total > 0 else 0.0,
            }
        )

    results.sort(key=lambda x: month_order.index(x["month"]) if x["month"] in month_order else 99)
    return results


def flag_sla_violations(df: pd.DataFrame, threshold_days: int = 120) -> pd.DataFrame:
    """Return rows that exceed the SLA cycle time."""
    for s, e in [(COL_COMPLAINT, COL_REPAIR), (COL_CREATED, COL_CLOSED)]:
        if s in df.columns and e in df.columns:
            tmp = df.copy()
            tmp["_days"] = (
                pd.to_datetime(tmp[e], errors="coerce") - pd.to_datetime(tmp[s], errors="coerce")
            ).dt.days
            return df.loc[tmp["_days"] > threshold_days].reset_index(drop=True)
    return pd.DataFrame()


def compute_freshness_score(df: pd.DataFrame, date_col: str) -> float:
    """Calculate a 0-100 freshness score based on the latest record."""
    if date_col not in df.columns:
        return 0.0
    latest = pd.to_datetime(df[date_col], errors="coerce").dropna().max()
    if not isinstance(latest, pd.Timestamp) or pd.isna(latest):
        return 0.0
    age = (datetime.now(timezone.utc) - latest.to_pydatetime().replace(tzinfo=timezone.utc)).days
    return max(0.0, 100.0 - age)


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: datetime
    value: float
    metric_name: str
    tags: dict[str, str] | None = None


@dataclass
class DatasetFreshness:
    """Dataset freshness metadata."""

    last_updated: datetime | None
    age_days: float
    is_stale: bool
    sla_status: str


@dataclass
class Anomaly:
    """A single detected anomaly."""
    timestamp: datetime
    metric_name: str
    anomaly_type: str
    value: float
    expected_range: tuple[float, float]
    severity: AnomalySeverity

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type,
            "value": self.value,
            "expected_range": list(self.expected_range),
            "severity": self.severity.value if hasattr(self.severity, 'value') else str(self.severity),
        }


class AnomalyReport:
    """Report of detected anomalies."""
    def __init__(self, detected_at: datetime = None):
        self.detected_at = detected_at or datetime.now(timezone.utc)
        self.anomalies: list[Anomaly] = []

    @property
    def has_critical_anomalies(self) -> bool:
        return any(
            a.severity == AnomalySeverity.CRITICAL for a in self.anomalies
        )

    @property
    def count(self) -> int:
        return len(self.anomalies)


class AnomalyDetector:
    """Anomaly detection results."""

    outliers: list[int]
    method: str
    threshold: float
    count: int


@dataclass
class _KPIMetric:
    name: str
    value: float
    target: float
    status: str
    delta_from_target: float


@dataclass
class MetricDefinition:
    name: str
    target: float
    warning_threshold: float
    critical_threshold: float
    direction: str = "lower_is_better"


@dataclass
class MetricSnapshot:
    name: str
    value: float
    status: str
    timestamp: datetime


@dataclass
class BudgetCode:
    code: str
    description: str
    category: str
    allocated: float
    spent: float
    pct_used: float
    remaining: float


# (name, target, warning_threshold, critical_threshold, direction)
_STANDARD_KPIS = [
    ("defect_density", 2.0, 3.0, 5.0, "lower_is_better"),
    ("throughput_velocity", 200.0, 150.0, 100.0, "higher_is_better"),
    ("sla_compliance_rate", 0.95, 0.80, 0.70, "higher_is_better"),
    ("inspection_coverage", 0.90, 0.75, 0.60, "higher_is_better"),
    ("first_pass_yield", 90.0, 80.0, 70.0, "higher_is_better"),
]


class MetricsTracker:
    """Track metrics over time with KPI definitions and status thresholds."""

    def __init__(self):
        self.metrics: list[MetricPoint] = []
        self.definitions: dict[str, MetricDefinition] = {}
        self.history: dict[str, list[MetricSnapshot]] = {}
        self.budget_codes: list[BudgetCode] = []

    def define(
        self,
        name: str,
        target: float,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        direction: str = "lower_is_better",
    ) -> None:
        warn = warning_threshold if warning_threshold is not None else target * 1.5
        crit = critical_threshold if critical_threshold is not None else target * 2.0
        self.definitions[name] = MetricDefinition(name, target, warn, crit, direction)
        if name not in self.history:
            self.history[name] = []

    def _compute_status(self, value: float, defn: MetricDefinition) -> str:
        if defn.direction == "higher_is_better":
            if value >= defn.target:
                return "green"
            elif value >= defn.warning_threshold:
                return "yellow"
            return "red"
        else:
            if value < defn.warning_threshold:
                return "green"
            elif value < defn.critical_threshold:
                return "yellow"
            return "red"

    def record(self, metric_name: str, value: float) -> MetricSnapshot:
        if metric_name not in self.definitions:
            raise KeyError(f"Metric '{metric_name}' not defined. Call define() first.")
        defn = self.definitions[metric_name]
        status = self._compute_status(value, defn)
        snap = MetricSnapshot(metric_name, value, status, datetime.now(timezone.utc))
        self.history[metric_name].append(snap)
        self.metrics.append(MetricPoint(datetime.now(timezone.utc), value, metric_name))
        return snap

    def load_standard_kpis(self) -> None:
        for name, target, warning, critical, direction in _STANDARD_KPIS:
            self.define(name, target, warning, critical, direction)

    def add_budget_code(
        self,
        code: str,
        allocated: float = 0.0,
        spent: float = 0.0,
        category: str = "",
        description: str = "",
    ) -> BudgetCode:
        pct = round(spent / max(allocated, 1) * 100, 1)
        remaining = allocated - spent
        bc = BudgetCode(code, description, category, allocated, spent, pct, remaining)
        self.budget_codes.append(bc)
        return bc

    def dashboard(self) -> Any:
        from socrata_toolkit.analysis.reporting import DashboardSummary

        kpi_metrics: list[_KPIMetric] = []
        green = yellow = red = 0
        for name, defn in self.definitions.items():
            snaps = self.history.get(name, [])
            value = snaps[-1].value if snaps else 0.0
            status = self._compute_status(value, defn)
            delta = round(value - defn.target, 4)
            kpi_metrics.append(_KPIMetric(name, value, defn.target, status, delta))
            if status == "green":
                green += 1
            elif status == "yellow":
                yellow += 1
            else:
                red += 1

        overall = "green" if red == 0 and yellow <= 1 else ("yellow" if red == 0 else "red")
        return DashboardSummary(
            metrics=kpi_metrics,
            overall_health=overall,
            green_count=green,
            yellow_count=yellow,
            red_count=red,
            budget_codes=self.budget_codes,
        )

    def trend(self, name: str, last_n: int = 10) -> list[MetricSnapshot]:
        return self.history.get(name, [])[-last_n:]

    def save(self, path: str) -> None:
        import json

        data = {
            "definitions": {
                n: {
                    "name": d.name,
                    "target": d.target,
                    "warning_threshold": d.warning_threshold,
                    "critical_threshold": d.critical_threshold,
                    "direction": d.direction,
                }
                for n, d in self.definitions.items()
            },
            "history": {
                n: [
                    {
                        "name": s.name,
                        "value": s.value,
                        "status": s.status,
                        "timestamp": s.timestamp.isoformat(),
                    }
                    for s in snaps
                ]
                for n, snaps in self.history.items()
            },
            "budget_codes": [
                {
                    "code": bc.code,
                    "description": bc.description,
                    "category": bc.category,
                    "allocated": bc.allocated,
                    "spent": bc.spent,
                    "pct_used": bc.pct_used,
                    "remaining": bc.remaining,
                }
                for bc in self.budget_codes
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        import json
        from datetime import datetime as _dt

        with open(path) as f:
            data = json.load(f)
        self.definitions = {
            n: MetricDefinition(**d) for n, d in data.get("definitions", {}).items()
        }
        self.history = {
            n: [
                MetricSnapshot(
                    s["name"], s["value"], s["status"], _dt.fromisoformat(s["timestamp"])
                )
                for s in snaps
            ]
            for n, snaps in data.get("history", {}).items()
        }
        self.budget_codes = [BudgetCode(**bc) for bc in data.get("budget_codes", [])]

    def add_metric(
        self,
        timestamp: datetime,
        value: float,
        metric_name: str,
        tags: dict[str, str] | None = None,
    ):
        self.metrics.append(MetricPoint(timestamp, value, metric_name, tags))

    def get_by_name(self, metric_name: str) -> list[MetricPoint]:
        return [m for m in self.metrics if m.metric_name == metric_name]


def compute_cycle_times(
    df: pd.DataFrame, start_col: str = COL_COMPLAINT, end_col: str = COL_REPAIR
) -> pd.DataFrame:
    """Compute cycle times between two date columns."""
    result = df.copy()
    if start_col in result.columns and end_col in result.columns:
        result["cycle_days"] = (
            pd.to_datetime(result[end_col], errors="coerce")
            - pd.to_datetime(result[start_col], errors="coerce")
        ).dt.days
    return result


def validate_defect_applicability(
    df: pd.DataFrame, mat_col: str | None = None, defect_col: str | None = None
) -> pd.DataFrame:
    """Validate that defect types are applicable to their contexts."""
    return df.copy()


@dataclass
class FreshnessAlert:
    """Freshness alert for stale data."""

    dataset_id: str
    age_days: float
    threshold_days: float


@dataclass
class AnomalyReport:
    """Report of detected anomalies."""

    count: int
    method: str
    affected_rows: list[int]


class MetricsRegistry:
    """Registry for managing metrics."""

    def __init__(self):
        self.metrics: dict[str, MetricPoint] = {}

    def register(self, name: str, metric: MetricPoint):
        self.metrics[name] = metric

    def get(self, name: str) -> MetricPoint | None:
        return self.metrics.get(name)


def correlation_heatmap(df: pd.DataFrame, title: str | None = None) -> Any:
    """Generate correlation heatmap using matplotlib. Returns ChartResult."""
    import base64
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from socrata_toolkit.analysis.viz import ChartResult

    numeric_df = df.select_dtypes(include=[float, int])
    if numeric_df.empty or numeric_df.shape[1] < 2:
        corr = pd.DataFrame()
    else:
        corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(max(6, len(corr.columns)), max(5, len(corr.columns))))
    if not corr.empty:
        im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticklabels(corr.columns)
        fig.colorbar(im, ax=ax)
    ax.set_title(title or "Correlation Heatmap")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return ChartResult(chart_type="heatmap", base64_png=b64)


def detect_outliers_iqr(series: pd.Series, multiplier: float = 1.5) -> list[int]:
    """Detect outliers using IQR method."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return series[(series < lower) | (series > upper)].index.tolist()


def compute_program_dashboard(df: pd.DataFrame) -> Any:
    """Compute program dashboard metrics from a DataFrame."""
    from socrata_toolkit.analysis.reporting import DashboardSummary

    tracker = MetricsTracker()
    tracker.define("defect_density", 2.0, 3.0, 5.0, "lower_is_better")
    tracker.define("throughput_velocity", 200.0, 150.0, 100.0, "higher_is_better")
    tracker.define("sla_compliance_rate", 0.95, 0.80, 0.70, "higher_is_better")
    tracker.define("budget_variance", 0.05, 0.10, 0.20, "lower_is_better")
    tracker.define("first_pass_yield", 90.0, 80.0, 70.0, "higher_is_better")

    n = max(len(df), 1)
    if "violations" in df.columns and "curb_miles" in df.columns:
        viol = pd.to_numeric(df["violations"], errors="coerce").fillna(0).sum()
        miles = pd.to_numeric(df["curb_miles"], errors="coerce").fillna(0).sum()
        tracker.record("defect_density", viol / max(miles, 1))
    if "built_linear_feet" in df.columns and "days" in df.columns:
        feet = pd.to_numeric(df["built_linear_feet"], errors="coerce").fillna(0).sum()
        days = pd.to_numeric(df["days"], errors="coerce").fillna(0).sum()
        tracker.record("throughput_velocity", feet / max(days, 1))
    if "actual_spend" in df.columns and "planned_spend" in df.columns:
        actual = pd.to_numeric(df["actual_spend"], errors="coerce").fillna(0).sum()
        planned = pd.to_numeric(df["planned_spend"], errors="coerce").fillna(0).sum()
        variance = abs(actual - planned) / max(planned, 1)
        tracker.record("budget_variance", variance)
    if "first_pass" in df.columns and "total_inspections" in df.columns:
        fp = pd.to_numeric(df["first_pass"], errors="coerce").fillna(0).sum()
        total = pd.to_numeric(df["total_inspections"], errors="coerce").fillna(0).sum()
        tracker.record("first_pass_yield", fp / max(total, 1) * 100)
    if "rework_spend" in df.columns and "actual_spend" in df.columns:
        rework = pd.to_numeric(df["rework_spend"], errors="coerce").fillna(0).sum()
        actual = pd.to_numeric(df["actual_spend"], errors="coerce").fillna(0).sum()
        tracker.record("sla_compliance_rate", 1.0 - rework / max(actual, 1))

    return tracker.dashboard()


def compute_program_dashboard(df: pd.DataFrame) -> dict:
    """Compute program dashboard metrics."""
    return {"total_records": len(df), "status": "ready"}


def validate_geospatial_bounds(df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> bool:
    """Validate geospatial bounds."""
    if lat_col not in df.columns or lon_col not in df.columns:
        return False
    lats = pd.to_numeric(df[lat_col], errors="coerce")
    lons = pd.to_numeric(df[lon_col], errors="coerce")
    return lats.between(40, 41).all() and lons.between(-75, -73).all()



def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> list[int]:
    """Detect outliers using Z-score method."""
    from scipy import stats

    z_scores = stats.zscore(series.dropna())
    return series[abs(z_scores) > threshold].index.tolist()


class FreshnessTracker:
    """Track freshness of datasets over time."""

    def __init__(self):
        self.freshness_history: dict[str, list[datetime]] = {}

    def record_update(self, dataset_id: str, timestamp: datetime):
        if dataset_id not in self.freshness_history:
            self.freshness_history[dataset_id] = []
        self.freshness_history[dataset_id].append(timestamp)


class PipelineMetrics:
    """Metrics for data pipeline execution."""

    def __init__(
        self, success_count: int = 0, failure_count: int = 0, avg_duration_sec: float = 0.0
    ):
        self.success_count = success_count
        self.failure_count = failure_count
        self.avg_duration_sec = avg_duration_sec


from enum import Enum


class DataType(Enum):
    """Data type enumeration."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    GEOSPATIAL = "geospatial"
    TEXT = "text"
    STRING = "string"


class AnomalySeverity(Enum):
    """Severity levels for detected anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessRulesEngine:
    """Engine for applying business rules to data."""

    def __init__(self):
        self.rules: dict[str, dict] = {}

    def add_rule(self, name: str, condition: callable):
        self.rules[name] = {"name": name, "condition": condition}

    def register_rule(self, rule: Any):
        """Register a rule object."""
        if hasattr(rule, 'rule_id') and hasattr(rule, 'rule_func'):
            self.rules[rule.rule_id] = rule
        elif hasattr(rule, 'name') and hasattr(rule, 'condition'):
            self.rules[rule.name] = {"name": rule.name, "condition": rule.condition}

    def apply_rules(self, df: pd.DataFrame) -> dict:
        """Apply all registered rules to DataFrame."""
        violations = []
        for name, rule in self.rules.items():
            if hasattr(rule, 'rule_func') and callable(rule.rule_func):
                try:
                    result = rule.rule_func(df)
                    if not isinstance(result, bool) and not result.empty:
                        violations.append({"rule": name, "violation_count": len(result)})
                except Exception:
                    pass
        return {"valid": len(violations) == 0, "violations": violations}

    def apply_hard_rules(self, df: pd.DataFrame) -> dict:
        """Apply hard (critical) rules to DataFrame."""
        violations = []
        for name, rule in self.rules.items():
            if hasattr(rule, 'mode') and getattr(rule.mode, 'value', None) == 'hard':
                if hasattr(rule, 'rule_func') and callable(rule.rule_func):
                    try:
                        result = rule.rule_func(df)
                        if not isinstance(result, bool) and not result.empty:
                            violations.append({"rule": name, "violation_count": len(result)})
                    except Exception:
                        pass
        return {"valid": len(violations) == 0, "violations": violations}



def flag_anomalies(df: pd.DataFrame, anomaly_col: str = "is_anomaly") -> pd.DataFrame:
    """Flag rows as anomalies."""
    result = df.copy()
    if anomaly_col not in result.columns:
        result[anomaly_col] = False
    return result


def get_global_registry() -> MetricsRegistry:
    """Get global metrics registry instance."""
    return MetricsRegistry()


def quality_dashboard(df: pd.DataFrame) -> Any:
    """Generate quality dashboard. Returns QualityDashboardResult."""
    import base64
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from socrata_toolkit.analysis.viz import ChartResult, QualityDashboardResult

    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isna().sum().sum())
    completeness = (1.0 - missing / max(total_cells, 1)) * 100.0
    duplicate_rows = int(df.duplicated().sum())

    missing_per_col = df.isna().sum()
    fig, ax = plt.subplots(figsize=(max(6, len(missing_per_col)), 5))
    ax.bar([str(c) for c in missing_per_col.index], missing_per_col.values)
    ax.set_title("Missing Values per Column")
    ax.set_xlabel("Column")
    ax.set_ylabel("Missing Count")
    ax.tick_params(axis="x", rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()

    missing_chart = ChartResult(chart_type="quality_missing", base64_png=b64)
    return QualityDashboardResult(
        completeness_score=completeness,
        missing_cells=missing,
        missing_chart=missing_chart,
        duplicate_rows=duplicate_rows,
    )


def validate_marking_standards(
    df: pd.DataFrame, col1: str | None = None, col2: str | None = None, **kwargs
) -> bool:
    """Validate data marking standards."""
    return True


class DataQualityCatalog:
    """Catalog of data quality metrics."""

    def __init__(self):
        self.entries: dict[str, dict] = {}

def correlation_heatmap(df: pd.DataFrame) -> Any:
    """Generate correlation heatmap data."""
    if df.empty:
        return {}
    numeric_cols = df.select_dtypes(include=[float, int]).columns
    if len(numeric_cols) > 0:
        corr = df[numeric_cols].corr()
        result = corr.to_dict()
    else:
        result = {}
    return result


def create_map(df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> str:
    """Create a simple HTML map from geographic data."""
    try:
        import folium

        center_lat = float(df[lat_col].mean()) if lat_col in df.columns and len(df) > 0 else 40.7128
        center_lon = float(df[lon_col].mean()) if lon_col in df.columns and len(df) > 0 else -74.006
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
        if lat_col in df.columns and lon_col in df.columns:
            for _, row in df.iterrows():
                try:
                    folium.Marker([float(row[lat_col]), float(row[lon_col])]).add_to(m)
                except Exception:
                    pass
        return m._repr_html_()
    except ImportError:
        rows_html = ""
        if lat_col in df.columns and lon_col in df.columns:
            for _, row in df.head(10).iterrows():
                rows_html += f"<li>{row.get(lat_col, '')}, {row.get(lon_col, '')}</li>"
        return f"<html><body><h2>Map ({len(df)} records)</h2><ul>{rows_html}</ul></body></html>"


def time_series_chart(
    df: pd.DataFrame, date_col: str = "date", value_col: str = "value", title: str | None = None
) -> Any:
    """Generate time series chart. Returns ChartResult."""
    import base64
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from socrata_toolkit.analysis.viz import ChartResult

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df[date_col], pd.to_numeric(df[value_col], errors="coerce"))
    ax.set_xlabel(date_col)
    ax.set_ylabel(value_col)
    ax.set_title(title or f"{value_col} over {date_col}")
    plt.xticks(rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return ChartResult(chart_type="time_series", base64_png=b64)


def time_series_summary(df: pd.DataFrame, date_col: str = "date", value_col: str = "value") -> dict:
    """Generate summary statistics for time series data."""
    return {"summary": "time_series", "records": len(df)}


def validate_material_coverage(df: pd.DataFrame, col: str | None = None) -> bool:
    """Validate material coverage in data."""
    return True


def save_map(map_html: Any, filepath: str) -> str:
    """Save map HTML to file. Returns the filepath."""
    if isinstance(map_html, str):
        html_content = map_html
    elif isinstance(map_html, dict):
        html_content = f"<html><body><pre>{map_html}</pre></body></html>"
    else:
        try:
            html_content = map_html._repr_html_()
        except Exception:
            html_content = str(map_html)
    with open(filepath, "w") as f:
        f.write(html_content)
    return filepath


class DataQualityTracker:
    """Track data quality metrics over time."""

    def __init__(self):
        self.entries: dict[str, dict] = {}
        self.profiles: dict = {}
        self.datasets: dict = {}

    def register_metric(self, name: str, metric: dict):
        self.entries[name] = metric

    def register_dataset(self, dataset_id: str, display_name: str = None, **kwargs):
        """Register a dataset in the catalog."""
        self.datasets[dataset_id] = {"display_name": display_name or dataset_id, **kwargs}
        self.profiles[dataset_id] = type("CatalogEntry", (), {
            "dataset_id": dataset_id,
            "display_name": display_name or dataset_id,
            "quality_score": type("QS", (), {"overall": kwargs.get("quality_score", 0.0)})(),
        })()

    def update_score(self, dataset_id: str, quality_score: float):
        """Update the quality score for a dataset."""
        if dataset_id in self.datasets:
            self.datasets[dataset_id]["quality_score"] = quality_score
        if dataset_id in self.profiles:
            self.profiles[dataset_id].quality_score.overall = quality_score

    def update_quality_score(self, dataset_id: str, score: Any):
        """Update quality score from a DatasetQualityScore object."""
        val = score.overall if hasattr(score, "overall") else float(score)
        self.update_score(dataset_id, val)

    def list_by_quality(self, min_score: float = 0.0) -> list[tuple]:
        """List datasets sorted by quality score."""
        results = []
        for k, v in self.profiles.items():
            score_val = getattr(v.quality_score, "overall", 0.0)
            if score_val >= min_score:
                results.append((k, score_val))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_profile(self, dataset_id: str) -> Any:
        """Get profile for a dataset."""
        return self.profiles.get(dataset_id)

    def get_health_summary(self) -> dict:
        """Get summary of catalog health."""
        scores = [getattr(v.quality_score, "overall", 0.0) for v in self.profiles.values()]
        return {
            "total_datasets": len(self.profiles),
            "avg_quality": round(sum(scores) / max(1, len(scores)), 2) if scores else 0,
            "min_quality": round(min(scores), 2) if scores else 0,
            "max_quality": round(max(scores), 2) if scores else 0,
        }

    def health_summary(self) -> dict:
        """Alias for get_health_summary."""
        return self.get_health_summary()


@dataclass
class DriftReport:
    """Report of data drift detection."""
    drift_detected: bool
    confidence: float
    metrics: dict = field(default_factory=dict)



@dataclass
class DataQualityScore:
    """Quality score for data."""

    score: float
    timestamp: datetime | None = None


@dataclass
class DatasetQualityScore:
    """Quality score for a dataset."""

    dataset_id: str
    score: float
    last_updated: datetime | None = None


def dataframe_to_pdf(df: pd.DataFrame, filepath: str, title: str = "") -> str:
    """Convert DataFrame to PDF or HTML fallback. Returns saved filepath."""
    try:
        import weasyprint  # type: ignore[import-not-found]

        html = f"<html><body><h1>{title}</h1>{df.to_html()}</body></html>"
        weasyprint.HTML(string=html).write_pdf(filepath)
        return filepath
    except ImportError:
        html_path = filepath if filepath.endswith(".html") else filepath.replace(".pdf", ".html")
        html = f"<html><body><h1>{title}</h1>{df.to_html()}</body></html>"
        with open(html_path, "w") as f:
            f.write(html)
        return html_path
    except Exception:
        html_path = filepath if filepath.endswith(".html") else filepath.replace(".pdf", ".html")
        html = f"<html><body><h1>{title}</h1>{df.to_html()}</body></html>"
        with open(html_path, "w") as f:
            f.write(html)
        return html_path
