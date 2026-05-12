from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Iterable

import pandas as pd

logger = logging.getLogger(__name__)

# ── Basic Profiling (Legacy & Core) ───────────────────────────────────────────

DataProfile = SimpleNamespace

def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Produce a profile of the dataframe for CLI and reporting."""
    profile = {
        "row_count": len(df),
        "column_count": df.shape[1],
        "null_counts": df.isna().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "columns": {
            col: {
                "dtype": str(df[col].dtype),
                "missing": int(df[col].isna().sum()),
                "unique": int(df[col].nunique(dropna=True)),
            }
            for col in df.columns
        }
    }
    numeric_df = df.select_dtypes(include="number")
    profile["numeric_summary"] = numeric_df.describe().to_dict() if not numeric_df.empty else {}
    return SimpleNamespace(**profile)

def quality_report(df: pd.DataFrame, key_columns: list[str]) -> dict[str, Any]:
    """Produce a simple quality report covering missing values and duplicates."""
    def _count_duplicate_rows(df: pd.DataFrame, keys: list[str]):
        full_dupes = df.duplicated(keep="first")
        key_dupes = df.duplicated(subset=keys, keep="first")
        return int((full_dupes & ~key_dupes).sum())

    return {
        "row_count": len(df),
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_rows": _count_duplicate_rows(df, key_columns),
        "duplicate_keys": {col: int(df.duplicated(subset=[col]).sum()) for col in key_columns}
    }

# ── Text Analytics ────────────────────────────────────────────────────────────

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']+")

@dataclass
class TextInsights:
    top_terms: list[tuple[str, int]]
    regex_hits: dict[str, int]
    tags: list[str]
    row_count: int

def generate_text_insights(df: pd.DataFrame, text_columns: list[str], regex_patterns: dict[str, str] | None = None, geo_column: str | None = None) -> tuple[pd.DataFrame, TextInsights]:
    """Analyze text columns for frequent terms, regex patterns, and descriptive tags."""
    patterns = regex_patterns or {
        "emails": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "phones": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "urls": r"https?://\S+",
        "ids": r"\b[A-Z]{2,}-?\d{2,}\b",
    }
    
    def top_terms(df, columns, limit=30):
        tokens = []
        for col in columns:
            if col in df.columns:
                for v in df[col].fillna(""):
                    tokens.extend(WORD_RE.findall(str(v).lower()))
        return Counter(t for t in tokens if len(t) >= 3).most_common(limit)

    def regex_scan(df, columns, patterns):
        out = {k: 0 for k in patterns}
        compiled = {k: re.compile(v, re.IGNORECASE) for k, v in patterns.items()}
        for col in columns:
            if col in df.columns:
                for text in df[col].fillna("").astype(str):
                    for name, cre in compiled.items():
                        if cre.search(text):
                            out[name] += 1
        return out

    tagged = df.copy()
    terms_list = top_terms(df, text_columns, limit=50)
    high_value_terms = {k for k, v in terms_list if v >= max(2, math.ceil(len(df) * 0.02))}
    
    tags_col = []
    for _, row in df.iterrows():
        row_tags = set()
        for col in text_columns:
            if col in df.columns:
                tokens = WORD_RE.findall(str(row.get(col, "")).lower())
                row_tags.update(t for t in tokens if t in high_value_terms)
        if geo_column and row.get(geo_column): row_tags.add("has_geo")
        if not row_tags: row_tags.add("untagged")
        tags_col.append(sorted(row_tags)[:15])
    
    tagged["descriptive_tags"] = tags_col
    insights = TextInsights(
        top_terms=terms_list[:30],
        regex_hits=regex_scan(df, text_columns, patterns),
        tags=sorted({t for tags in tags_col for t in tags}),
        row_count=len(df)
    )
    return tagged, insights

# ── NYC SDM & ADA Validation ──────────────────────────────────────────────────

@dataclass
class ValidationReport:
    valid: bool
    errors: list[str]
    warnings: list[str]
    affected_records: int = 0

VALID_MATERIALS = {"Hot Mix Asphalt (HMA)", "Stone Matrix Asphalt (SMA)", "PCC", "concrete", "asphalt"} # Simplified for core
ADA_REQUIREMENTS = {
    "clear_path_width": {"min_feet": 5.0},
    "running_slope": {"max_percent": 5.0},
    "level_change": {"max_inches": 0.5},
}

def validate_required_columns(df: pd.DataFrame, required: list[str]) -> ValidationReport:
    missing = [c for c in required if c not in df.columns]
    return ValidationReport(valid=not missing, errors=[f"Missing column: {c}" for c in missing], warnings=[])

def validate_geospatial_bounds(df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> ValidationReport:
    bounds = {"min_lat": 40.4774, "max_lat": 40.9176, "min_lon": -74.2591, "max_lon": -73.7004}
    if lat_col not in df.columns or lon_col not in df.columns:
        return ValidationReport(False, ["Geo columns missing"], [])
    out_lat = (df[lat_col] < bounds["min_lat"]) | (df[lat_col] > bounds["max_lat"])
    out_lon = (df[lon_col] < bounds["min_lon"]) | (df[lon_col] > bounds["max_lon"])
    affected = int((out_lat | out_lon | df[lat_col].isna() | df[lon_col].isna()).sum())
    return ValidationReport(valid=affected == 0, errors=[f"{affected} records out of NYC bounds"] if affected else [], warnings=[], affected_records=affected)

def validate_ada_compliance_gates(df: pd.DataFrame, ada_col: str = "ada_compliant", width_col: str | None = None) -> ValidationReport:
    errors = []
    if ada_col not in df.columns: return ValidationReport(False, [f"Column {ada_col} missing"], [])
    null_count = int(df[ada_col].isna().sum())
    if null_count: errors.append(f"{null_count} segments missing compliance scoring")
    return ValidationReport(valid=not errors, errors=errors, warnings=[], affected_records=null_count)

# ── Statistical Anomaly & Drift Detection ─────────────────────────────────────

class AnomalySeverity(Enum):
    CRITICAL = "critical"; HIGH = "high"; MEDIUM = "medium"; LOW = "low"; INFO = "info"

@dataclass
class Anomaly:
    timestamp: datetime
    metric_name: str
    anomaly_type: str
    value: float
    expected_range: Tuple[float, float]
    severity: AnomalySeverity
    z_score: Optional[float] = None
    explanation: str = ""

class AnomalyDetector:
    def __init__(self, z_score_threshold: float = 3.0, min_history: int = 5):
        self.z_score_threshold = z_score_threshold
        self.min_history = min_history

    def detect_outliers(self, metric_name: str, metric_history: List[Tuple[datetime, float]]) -> list[Anomaly]:
        if len(metric_history) < self.min_history: return []
        values = [v for _, v in metric_history]
        mean = sum(values) / len(values)
        std_dev = math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))
        if std_dev == 0: return []
        z = (values[-1] - mean) / std_dev
        if abs(z) > self.z_score_threshold:
            return [Anomaly(metric_history[-1][0], metric_name, "z_score", values[-1], (mean-3*std_dev, mean+3*std_dev), AnomalySeverity.HIGH, z, f"Z-score {z:.2f}")]
        return []

# ── SLA & Freshness Tracking ──────────────────────────────────────────────────

@dataclass
class SLAMetrics:
    avg_total_cycle_days: float
    sla_compliance_rate: float
    violations_count: int
    by_borough: Dict[str, Any]

def compute_sla_metrics(df: pd.DataFrame, start_col: str = "complaint_date", end_col: str = "repair_date") -> SLAMetrics:
    if start_col not in df.columns or end_col not in df.columns:
        return SLAMetrics(0, 100, 0, {})
    tmp = df.copy()
    tmp["_days"] = (pd.to_datetime(tmp[end_col], errors="coerce") - pd.to_datetime(tmp[start_col], errors="coerce")).dt.days
    clean = tmp["_days"].dropna()
    violations = int((clean > 120).sum())
    return SLAMetrics(
        avg_total_cycle_days=round(float(clean.mean()), 1) if not clean.empty else 0,
        sla_compliance_rate=round((1 - violations/max(len(clean),1))*100, 1) if not clean.empty else 100,
        violations_count=violations,
        by_borough={}
    )

def detect_outliers_iqr(df: pd.DataFrame, column: str) -> pd.Series:
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    return (df[column] < (q1 - 1.5 * iqr)) | (df[column] > (q3 + 1.5 * iqr))

def detect_outliers_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.Series:
    mean = df[column].mean()
    std = df[column].std()
    if std == 0: return pd.Series([False] * len(df))
    return ((df[column] - mean).abs() / std) > threshold

def detect_all_outliers(df: pd.DataFrame) -> Dict[str, int]:
    num_cols = df.select_dtypes(include="number").columns
    return {col: int(detect_outliers_iqr(df, col).sum()) for col in num_cols}

def correlation_analysis(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include="number").corr()

def time_series_summary(df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col])
    return {"mean": tmp[value_col].mean(), "max": tmp[value_col].max()}

def classify_distribution(series: pd.Series) -> str:
    if series.nunique() < 10: return "categorical"
    return "numeric"

def classify_all_distributions(df: pd.DataFrame) -> Dict[str, str]:
    return {col: classify_distribution(df[col]) for col in df.columns}

def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_is_anomaly"] = False
    return out

# ── Program Metrics & Dashboards ──────────────────────────────────────────────

@dataclass
class MetricSnapshot:
    name: str
    value: float
    timestamp: str
    status: str
    target: float
    delta_from_target: float

class MetricsTracker:
    def __init__(self):
        self.history: Dict[str, List[MetricSnapshot]] = {}

    def record(self, name: str, value: float, target: float = 0.0) -> MetricSnapshot:
        status = "green" if value >= target else "red"
        snap = MetricSnapshot(name, value, datetime.now(timezone.utc).isoformat(), status, target, value - target)
        if name not in self.history: self.history[name] = []
        self.history[name].append(snap)
        return snap

def compute_program_dashboard(df: pd.DataFrame) -> Any:
    tracker = MetricsTracker()
    if "violations" in df.columns:
        tracker.record("defect_density", df["violations"].mean(), target=2.0)
    return SimpleNamespace(metrics=[s[-1] for s in tracker.history.values()], overall_health="green", green_count=len(tracker.history), yellow_count=0, red_count=0)

# ── Visualizations ────────────────────────────────────────────────────────────

def histogram(df: pd.DataFrame, column: str) -> Any:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    df[column].hist(ax=ax)
    return fig

def bar_chart(df: pd.DataFrame, column: str) -> Any:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    df[column].value_counts().plot(kind="bar", ax=ax)
    return fig

def correlation_heatmap(df: pd.DataFrame) -> Any:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    df.select_dtypes(include="number").corr().style.background_gradient(cmap="coolwarm")
    return fig
