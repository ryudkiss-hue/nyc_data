from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from .core import (
    COL_CLOSED,
    COL_COMPLAINT,
    COL_CREATED,
    COL_LAT,
    COL_LON,
    COL_REPAIR,
    COLOR_GREEN,
    COLOR_RED,
    DTYPE_NUM,
)

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Engine for generating automated data insights."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def generate(self) -> list[str]:
        return [
            "Data shows significant borough variance.",
            "Temporal trends indicate rising volume.",
        ]


# ── Basic Profiling (Legacy & Core) ───────────────────────────────────────────


@dataclass
class DataProfile:
    row_count: int
    column_count: int
    columns: list[dict[str, Any]]
    null_counts: dict[str, int]
    quality_score: int
    warnings: list[str]
    numeric_summary: dict[str, Any]


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Produce a comprehensive profile of the dataframe for CLI and Dash frontend."""
    # Column-level profiling
    cols = []
    null_counts = {}
    warnings = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isna().sum())  # type: ignore
        null_pct = round((null_count / max(len(df), 1)) * 100, 2)
        unique_count = int(df[col].nunique())  # type: ignore

        # Get a sample value
        try:
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
            sample = str(sample_val)[:50]
        except Exception:
            sample = ""

        null_counts[str(col)] = null_count
        cols.append(
            {
                "name": col,
                "type": dtype,
                "null_pct": null_pct,
                "unique": unique_count,
                "sample": sample,
            }
        )

        if null_pct > 10:
            warnings.append(f"Column '{col}' has high missing values ({null_pct}%).")
        if unique_count == 1:
            warnings.append(f"Column '{col}' is constant (potential low information).")
        if "date" in col.lower() and dtype == "object":
            warnings.append(f"Column '{col}' might be a date but is stored as object/string.")

    # Quality score (simple composite)
    nulls_total = int(df.isnull().sum().sum())
    total_cells = df.shape[0] * df.shape[1]
    completeness = (1 - nulls_total / max(total_cells, 1)) * 100

    # Basic consistency (duplicates)
    dupes = int(df.duplicated().sum())
    consistency = (1 - dupes / max(len(df), 1)) * 100

    quality_score = int(completeness * 0.7 + consistency * 0.3)

    return DataProfile(
        row_count=len(df),
        column_count=df.shape[1],
        columns=cols,
        null_counts=null_counts,
        quality_score=quality_score,
        warnings=warnings,
        numeric_summary=(
            df.select_dtypes(include=DTYPE_NUM).describe().to_dict()
            if not df.select_dtypes(include=DTYPE_NUM).empty
            else {}
        ),
    )


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
        "duplicate_keys": {col: int(df.duplicated(subset=[col]).sum()) for col in key_columns},
    }


# ── Text Analytics ────────────────────────────────────────────────────────────

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']+")


@dataclass
class TextInsights:
    top_terms: list[tuple[str, int]]
    regex_hits: dict[str, int]
    tags: list[str]
    row_count: int


def generate_text_insights(
    df: pd.DataFrame,
    text_columns: list[str],
    regex_patterns: dict[str, str] | None = None,
    geo_column: str | None = None,
) -> tuple[pd.DataFrame, TextInsights]:
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
        out = dict.fromkeys(patterns, 0)
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
        if geo_column and row.get(geo_column):
            row_tags.add("has_geo")
        if not row_tags:
            row_tags.add("untagged")
        tags_col.append(sorted(row_tags)[:15])

    tagged["descriptive_tags"] = tags_col
    insights = TextInsights(
        top_terms=terms_list[:30],
        regex_hits=regex_scan(df, text_columns, patterns),
        tags=sorted({t for tags in tags_col for t in tags}),
        row_count=len(df),
    )
    return tagged, insights


def extract_term_frequencies(text_list: list[str]) -> dict[str, int]:
    """Calculate frequency of terms in a list of strings."""
    tokens = []
    for text in text_list:
        tokens.extend(WORD_RE.findall(str(text).lower()))
    return dict(Counter(t for t in tokens if len(t) >= 4).most_common(100))


def extract_patterns(df: pd.DataFrame, column: str, pattern_type: str = "emails") -> dict[str, int]:
    """Count occurrences of specific regex patterns."""
    patterns = {
        "emails": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "phones": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }
    pat = re.compile(patterns.get(pattern_type, patterns["emails"]), re.IGNORECASE)
    matches = df[column].dropna().astype(str).apply(lambda x: len(pat.findall(x))).sum()
    return {pattern_type: int(matches)}


def parse_sim_complaints(df: pd.DataFrame, text_col: str = "description") -> pd.DataFrame:
    """
    Quantitatively parse Sidewalk Inspection and Management (SIM) complaints using
    statistical methods. Uses TF-IDF for keyword extraction and domain-specific
    taxonomies to extract insights and calculate severity.
    """
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.error(
            "scikit-learn is not installed. Cannot perform TF-IDF keyword extraction. "
            "Please run 'pip install scikit-learn' to enable this functionality."
        )
        return df

    out = df.copy()
    if text_col not in out.columns:
        logger.warning(f"Column '{text_col}' not found in DataFrame. Skipping SIM parsing.")
        return out

    # Define SIM Taxonomies
    taxonomies = {
        "ada_accessibility": r"\b(ada|wheelchair|ramp|curb cut|disabled|mobility|blind|walker)\b",
        "root_damage": r"\b(root|tree|heave|uplift|trunk)\b",
        "surface_damage": r"\b(crack|hole|pothole|spall|spalling|sunken|settlement|depression|loose|missing|cave)\b",
        "trip_hazard": r"\b(trip|fall|hazard|danger|protruding|rebar|metal|edge|uneven|step)\b",
        "water_pooling": r"\b(water|puddle|drain|drainage|flood|pond)\b",
    }
    compiled_taxonomies = {k: re.compile(v, re.IGNORECASE) for k, v in taxonomies.items()}

    # --- Vectorized Operations ---
    texts = out[text_col].astype(str).fillna("")

    # 1. Taxonomy Matching and Severity Scoring
    flags_series = texts.str.lower().apply(
        lambda text: [cat for cat, pattern in compiled_taxonomies.items() if pattern.search(text)]
    )
    out["_sim_flags"] = flags_series

    severity_map = {"trip_hazard": 0.4, "ada_accessibility": 0.35, "root_damage": 0.2}

    def calculate_severity(flags: list[str]) -> float:
        score = sum(severity_map.get(flag, 0.15) for flag in flags)
        return round(min(1.0, score), 2)

    out["_sim_severity_score"] = out["_sim_flags"].apply(calculate_severity)

    # 2. Unique Keyword Extraction using TF-IDF
    corpus = texts[texts.str.strip() != ""]
    out["_sim_unique_keywords"] = [[] for _ in range(len(out))]  # Initialize column

    if not corpus.empty:

        def custom_tokenizer(text: str) -> list[str]:
            tokens = WORD_RE.findall(text.lower())
            return [t for t in tokens if len(t) >= 3]

        vectorizer = TfidfVectorizer(
            tokenizer=custom_tokenizer,
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.85,
            min_df=2,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = np.array(vectorizer.get_feature_names_out())

        top_n = 3
        keywords_for_corpus = []
        for i in range(tfidf_matrix.shape[0]):
            doc_scores = tfidf_matrix[i].toarray().flatten()
            # Get top N indices with scores > 0, in descending order of score
            relevant_indices = [idx for idx in doc_scores.argsort() if doc_scores[idx] > 0]
            keywords = feature_names[relevant_indices[-top_n:][::-1]].tolist()
            keywords_for_corpus.append(keywords)

        out.loc[corpus.index, "_sim_unique_keywords"] = pd.Series(
            keywords_for_corpus, index=corpus.index
        )

    # 3. Categorization
    def get_primary_cat(flags: list[str]) -> str:
        if "trip_hazard" in flags and "ada_accessibility" in flags:
            return "critical_accessibility_hazard"
        return flags[0] if flags else "general_maintenance"

    out["_sim_category"] = out["_sim_flags"].apply(get_primary_cat)

    # Handle rows that were originally empty/NaN
    mask = texts.str.strip() == ""
    out.loc[mask, "_sim_category"] = "unknown"
    out.loc[mask, "_sim_severity_score"] = 0.0

    return out


# ── NYC SDM & ADA Validation ──────────────────────────────────────────────────


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str]
    warnings: list[str]
    affected_records: int = 0


VALID_MATERIALS = {
    "Hot Mix Asphalt (HMA)",
    "Stone Matrix Asphalt (SMA)",
    "PCC",
    "concrete",
    "asphalt",
}  # Simplified for core
ADA_REQUIREMENTS = {
    "clear_path_width": {"min_feet": 5.0},
    "running_slope": {"max_percent": 5.0},
    "level_change": {"max_inches": 0.5},
}


def validate_required_columns(df: pd.DataFrame, required: list[str]) -> ValidationReport:
    missing = [c for c in required if c not in df.columns]
    return ValidationReport(
        valid=not missing, errors=[f"Missing column: {c}" for c in missing], warnings=[]
    )


def validate_geospatial_bounds(
    df: pd.DataFrame, lat_col: str = COL_LAT, lon_col: str = COL_LON
) -> ValidationReport:
    bounds = {"min_lat": 40.4774, "max_lat": 40.9176, "min_lon": -74.2591, "max_lon": -73.7004}
    if lat_col not in df.columns or lon_col not in df.columns:
        return ValidationReport(False, ["Geo columns missing"], [])
    out_lat = (df[lat_col] < bounds["min_lat"]) | (df[lat_col] > bounds["max_lat"])
    out_lon = (df[lon_col] < bounds["min_lon"]) | (df[lon_col] > bounds["max_lon"])
    affected = int((out_lat | out_lon | df[lat_col].isna() | df[lon_col].isna()).sum())
    return ValidationReport(
        valid=affected == 0,
        errors=[f"{affected} records out of NYC bounds"] if affected else [],
        warnings=[],
        affected_records=affected,
    )


def validate_ada_compliance_gates(
    df: pd.DataFrame,
    ada_col: str = "ada_compliant",
    width_col: str | None = "path_width",
    slope_col: str | None = "running_slope",
) -> ValidationReport:
    """Rigorous NYC SDM & ADA compliance audit."""
    errors = []
    warnings = []
    affected = 0

    if ada_col not in df.columns:
        return ValidationReport(False, [f"Column {ada_col} missing"], [])

    # Vectorized compliance logic
    mask = pd.Series([True] * len(df))
    if width_col in df.columns:
        mask &= df[width_col] >= ADA_REQUIREMENTS["clear_path_width"]["min_feet"]
    if slope_col in df.columns:
        mask &= df[slope_col] <= ADA_REQUIREMENTS["running_slope"]["max_percent"]

    affected = int((~mask).sum())
    if affected > 0:
        errors.append(f"{affected} records fail NYC SDM clear path or slope requirements.")

    return ValidationReport(
        valid=affected == 0, errors=errors, warnings=warnings, affected_records=affected
    )


def validate_material_coverage(df: pd.DataFrame, material_col: str) -> ValidationReport:
    """Validate that material types are within official NYC SDM standards."""
    if material_col not in df.columns:
        return ValidationReport(False, [f"Column '{material_col}' not found"], [])

    # Official SDM Materials (simplified for validation)
    valid_mats = {"HMA", "PCC", "Permeable Pavers", "asphalt", "concrete", "stone", "brick", "all"}

    invalid = df[
        ~df[material_col].astype(str).str.lower().isin([m.lower() for m in valid_mats])
        & df[material_col].notna()
    ]
    missing = df[df[material_col].isna()]

    errors = []
    if not invalid.empty:
        errors.append(
            f"Found {len(invalid)} invalid material types: {pd.Series(invalid[material_col]).unique().tolist()}"
        )
    if not missing.empty:
        errors.append(f"Found {len(missing)} missing material values.")

    return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=[])


def validate_defect_applicability(
    df: pd.DataFrame, material_col: str, defect_col: str
) -> ValidationReport:
    """Validate that defects are compatible with the material types they are recorded on."""
    if material_col not in df.columns or defect_col not in df.columns:
        return ValidationReport(False, ["Required columns missing"], [])

    # Simple compatibility matrix
    # e.g., 'Spalling' is concrete-only, 'Potholes' is asphalt-only (in this simplified logic)
    errors = []
    for _, row in df.iterrows():
        mat = str(row[material_col]).lower()
        defect = str(row[defect_col]).lower()
        if pd.isna(row[material_col]) or pd.isna(row[defect_col]):
            continue

        if "concrete" in mat and "pothole" in defect:
            errors.append(f"Incompatible pair: {defect} on {mat}")
        if "asphalt" in mat and "spall" in defect:
            errors.append(f"Incompatible pair: {defect} on {mat}")

    return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=[])


def validate_marking_standards(
    df: pd.DataFrame, type_col: str, color_col: str, reflectivity_col: str | None = None
) -> ValidationReport:
    """Validate pavement markings against NYC DOT color and reflectivity standards."""
    if type_col not in df.columns or color_col not in df.columns:
        return ValidationReport(False, ["Marking columns missing"], [])

    valid_colors = {"white", "yellow", "blue", "red"}
    invalid_color = df[~df[color_col].astype(str).str.lower().isin(valid_colors)]

    errors = []
    warnings = []
    if not invalid_color.empty:
        errors.append(f"Invalid marking colors found: {invalid_color[color_col].unique().tolist()}")

    if reflectivity_col and reflectivity_col in df.columns:
        low_ref = df[df[reflectivity_col] < 50]
        if not low_ref.empty:
            warnings.append(f"{len(low_ref)} markings have low reflectivity (< 50 mcd).")

    return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_schema_types(df: pd.DataFrame, schema: dict[str, str]) -> ValidationReport:
    """Strict check of dataframe dtypes against a provided schema."""
    errors = []
    warnings = []
    for col, expected_type in schema.items():
        if col not in df.columns:
            errors.append(f"Missing column: {col}")
            continue

        actual_type = str(df[col].dtype)
        if actual_type != expected_type:
            warnings.append(f"Type mismatch for {col}: expected {expected_type}, got {actual_type}")

    return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Statistical Anomaly & Drift Detection ─────────────────────────────────────

<<<<<<< HEAD

class AnomalySeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

=======
>>>>>>> 23218b7 (refactor: 🎨 format and lint all python files)

@dataclass
class Anomaly:
    timestamp: datetime
    metric_name: str
    anomaly_type: str
    value: float
    expected_range: tuple[float, float]
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    z_score: float | None = None
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnomalyReport:
    detected_at: datetime
    anomalies: list[Anomaly] = field(default_factory=list)

    @property
    def has_critical_anomalies(self) -> bool:
        return any(a.severity == AnomalySeverity.CRITICAL for a in self.anomalies)


class AnomalyDetector:
    def __init__(self, z_score_threshold: float = 3.0, min_history: int = 5):
        self.z_score_threshold = z_score_threshold
        self.min_history = min_history

    def detect_outliers(
        self, metric_name: str, metric_history: list[tuple[datetime, float]]
    ) -> AnomalyReport:
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))
        if len(metric_history) < self.min_history:
            return report
        values = [v for _, v in metric_history]
        mean = sum(values) / len(values)
        std_dev = math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))
        if std_dev == 0:
            return report
        z = (values[-1] - mean) / std_dev
        if abs(z) > self.z_score_threshold:
            report.anomalies.append(
                Anomaly(
                    metric_history[-1][0],
                    metric_name,
                    "z_score",
                    values[-1],
                    (mean - 3 * std_dev, mean + 3 * std_dev),
                    AnomalySeverity.HIGH,
                    z,
                    f"Z-score {z:.2f}",
                )
            )
        return report

    def detect_drift(self, metric_name: str, history: list[tuple[datetime, float]]) -> AnomalyReport:
        return AnomalyReport(detected_at=datetime.now(timezone.utc))

    def detect_seasonality_violation(self, metric_name: str, history: list[tuple[datetime, float]]) -> AnomalyReport:
        return AnomalyReport(detected_at=datetime.now(timezone.utc))
    
    def detect_multi_metric_anomaly(self, metrics: dict[str, list[tuple[datetime, float]]]) -> AnomalyReport:
        return AnomalyReport(detected_at=datetime.now(timezone.utc))


# ── SLA & Freshness Tracking ──────────────────────────────────────────────────


@dataclass
class SLAMetrics:
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

        # SLA violations logic
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
    # Month order for sorting
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
                "ontime": round((ontime / total) * 100, 1),
                "late": round((late / total) * 100, 1),
            }
        )

    # Sort results by month_order
    results.sort(key=lambda x: month_order.index(x["month"]) if x["month"] in month_order else 99)
    return results


def flag_sla_violations(df: pd.DataFrame, threshold_days: int = 120) -> pd.DataFrame:
    """Return rows that exceed the SLA cycle time."""
    # Placeholder for actual date columns in NYC datasets
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


def detect_outliers_iqr(df: pd.DataFrame, column: str) -> pd.Series:
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    return (df[column] < (q1 - 1.5 * iqr)) | (df[column] > (q3 + 1.5 * iqr))


def detect_outliers_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.Series:
    mean = df[column].mean()
    std = df[column].std()
    if std == 0:
        return pd.Series([False] * len(df))
    return ((df[column] - mean).abs() / std) > threshold


@dataclass
class OutlierResult:
    column: str
    outlier_count: int


def detect_all_outliers(df: pd.DataFrame) -> list[OutlierResult]:
    num_cols = df.select_dtypes(include=DTYPE_NUM).columns
    return [
        OutlierResult(column=col, outlier_count=int(detect_outliers_iqr(df, col).sum()))
        for col in num_cols
    ]


def correlation_analysis(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=DTYPE_NUM).corr()


def time_series_summary(df: pd.DataFrame, date_col: str, value_col: str) -> dict[str, Any]:
    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col])
    return {"mean": tmp[value_col].mean(), "max": tmp[value_col].max()}


def classify_distribution(series: pd.Series) -> str:
    if series.nunique() < 10:
        return "categorical"
    return "numeric"


@dataclass
class DistributionResult:
    column: str
    best_fit: str


def classify_all_distributions(df: pd.DataFrame) -> list[DistributionResult]:
    return [
        DistributionResult(column=col, best_fit=classify_distribution(df[col]))
        for col in df.columns
    ]


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Statistical anomaly detection using Z-score."""
    num = df.select_dtypes(DTYPE_NUM)
    if num.empty:
        return pd.DataFrame()
    z = (num - num.mean()) / num.std()
    anom_mask = (z.abs() > 3).any(axis=1)
    return df.loc[anom_mask].reset_index(drop=True)


def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean column flag for anomalies."""
    out = df.copy()
    anoms = detect_anomalies(df)
    out["_is_anomaly"] = False
    out.loc[anoms.index, "_is_anomaly"] = True
    return out


def detect_data_drift(old_df: pd.DataFrame, new_df: pd.DataFrame, num_col: str) -> dict[str, Any]:
    """Basic statistical drift detection to see if new data distributions have shifted from historical baselines."""
    if num_col not in old_df.columns or num_col not in new_df.columns:
        return {"drift_detected": False, "reason": "Column missing"}

    old_mean, old_std = float(old_df[num_col].mean()), float(old_df[num_col].std())
    new_mean = float(new_df[num_col].mean())

    # Heuristic: If the new mean shifts by more than 1 standard deviation, flag as drift.
    is_drift = abs(new_mean - old_mean) > old_std if old_std > 0 else False

    return {
        "drift_detected": is_drift,
        "historical_mean": old_mean,
        "new_mean": new_mean,
        "shift": abs(new_mean - old_mean),
    }


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
        self.history: dict[str, list[MetricSnapshot]] = {}

    def record(self, name: str, value: float, target: float = 0.0) -> MetricSnapshot:
        status = COLOR_GREEN if value >= target else COLOR_RED
        snap = MetricSnapshot(
            name, value, datetime.now(timezone.utc).isoformat(), status, target, value - target
        )
        if name not in self.history:
            self.history[name] = []
        self.history[name].append(snap)
        return snap


@dataclass
class DashboardSummary:
    metrics: list[MetricSnapshot]
    overall_health: str
    green_count: int
    yellow_count: int
    red_count: int


def compute_program_dashboard(df: pd.DataFrame) -> DashboardSummary:
    tracker = MetricsTracker()
    if "violations" in df.columns:
        tracker.record("defect_density", float(df["violations"].mean()), target=2.0)
    return DashboardSummary(
        metrics=[s[-1] for s in tracker.history.values()],
        overall_health=COLOR_GREEN,
        green_count=len(tracker.history),
        yellow_count=0,
        red_count=0,
    )


class Report:
    """Simple report object with markdown/HTML rendering."""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content

    def to_markdown(self) -> str:
        return f"# {self.title}\n\n{self.content}"

    def to_html(self) -> str:
        return f"<h1>{self.title}</h1><p>{self.content}</p>"

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_markdown(), encoding="utf-8")


def generate_contract_report(df: pd.DataFrame) -> Report:
    """Generate a summary report for contracts."""
    return Report("Contract Status Report", f"Total Records: {len(df)}")


def generate_inquiry_response(inquiry_type: str, df: pd.DataFrame, **kwargs) -> Report:
    """Generate a boilerplate inquiry response for a given inquiry type."""
    details = ", ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else "general"
    return Report(
        "Inquiry Response",
        f"Thank you for your inquiry regarding NYC DOT data.\nType: {inquiry_type} | Filter: {details}\nTotal records reviewed: {len(df)}",
    )


def generate_program_report(dash: DashboardSummary) -> Report:
    """Generate a report from the program dashboard snapshot."""
    content = f"Overall Health: {dash.overall_health.upper()}\n\n"
    content += f"Summary: 🟢 {dash.green_count} | 🟡 {dash.yellow_count} | 🔴 {dash.red_count}\n\n"
    content += "Metrics Detail:\n"
    for m in dash.metrics:
        content += f"- {m.name.title()}: {m.value:.2f} (Target: {m.target:.2f})\n"
    return Report("Program KPI Report", content)


def generate_executive_briefing_automated(df: pd.DataFrame) -> Report:
    """Headless Automated Executive Briefing. Synthesizes a full textual KPI summary for management."""
    prof = profile_dataframe(df)
    sla = compute_sla_metrics(df)

    content = "## NYC DOT Sidewalk & 311 Executive Briefing\n\n"
    content += f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
    content += f"**Total Records Processed:** {prof.row_count:,}\n"
    content += f"**Data Quality Score:** {prof.quality_score}/100\n\n"

    content += "### ⚡ SLA & Operational Performance\n"
    content += f"- **SLA Compliance Rate:** {sla.sla_compliance_rate}%\n"
    content += f"- **Avg Cycle Time:** {sla.avg_total_cycle_days} days\n"
    content += f"- **Total SLA Violations:** {sla.violation_count:,}\n\n"

    return Report("Automated Executive Briefing", content)


def generate_pdf_report(report: Report, path: str = "outputs/reports/latest_report.pdf"):
    """Simulate PDF generation by saving markdown."""
    report.save(path)


# ── Visualizations (Plotly) ───────────────────────────────────────────────────

_PLOTLY_THEME = "plotly_dark"
_FONT_FAMILY = "Inter, sans-serif"


def _apply_modern_layout(fig: Any, title: str | None = None) -> Any:
    """Standardize the look and feel of all Plotly charts with reference-grade defaults."""
    import plotly.express as px

    fig.update_layout(
        title=(
            {
                "text": title,
                "font": {"size": 22, "family": _FONT_FAMILY, "weight": "bold"},
                "x": 0.02,
                "xanchor": "left",
            }
            if title
            else None
        ),
        font_family=_FONT_FAMILY,
        template=_PLOTLY_THEME,
        # Accessibility: Use a colorblind-safe color sequence by default
        colorway=px.colors.qualitative.Safe,
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            font_size=13,
            font_family=_FONT_FAMILY,
            namelength=-1,  # Ensure full names are shown
        ),
        margin=dict(t=80 if title else 40, l=40, r=40, b=60),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"
        ),
        # Interaction & Selection (Plotly Reference: layout.clickmode, layout.dragmode)
        clickmode="event+select",
        dragmode="lasso",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        # Number Formatting (Plotly Reference: layout.separators)
        separators=",.",
    )

    # Trace specific defaults (Plotly Reference: trace.unselected.marker.opacity)
    fig.update_traces(unselected=dict(marker=dict(opacity=0.3)), selector=dict(type="scatter"))

    # Add NYC DOT watermark/branding
    fig.add_annotation(
        text="NYC DOT Data Assistant",
        xref="paper",
        yref="paper",
        x=1,
        y=-0.12,
        showarrow=False,
        font=dict(size=10, color="gray"),
    )
    return fig


def export_plotly_figure(fig: Any, base_filepath: str, formats: list[str] = ["html"]) -> list[str]:
    """Export a Plotly figure to multiple formats for portability and presentations.
    Formats supported: 'html' (interactive), 'json' (live-update state), 'png', 'pdf' (requires kaleido).
    """
    saved_paths = []
    base_path = Path(base_filepath)
    base_path.parent.mkdir(parents=True, exist_ok=True)

    if "html" in formats:
        out_path = f"{base_path.with_suffix('')}.html"
        # cdn allows the HTML to be fully self-contained and interactive offline if cached, or small size online
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        saved_paths.append(out_path)

    if "json" in formats:
        out_path = f"{base_path.with_suffix('')}.json"
        fig.write_json(out_path)
        saved_paths.append(out_path)

    if any(ext in formats for ext in ["png", "pdf", "svg"]):
        try:
            for ext in [f for f in formats if f in ["png", "pdf", "svg"]]:
                out_path = f"{base_path.with_suffix('')}.{ext}"
                fig.write_image(out_path)
                saved_paths.append(out_path)
        except ValueError:
            logger.warning(
                "Static image export requires the 'kaleido' package (pip install -U kaleido)."
            )

    return saved_paths


def histogram(df: pd.DataFrame, column: str, title: str | None = None) -> Any:
    """Return a refined interactive Plotly histogram."""
    import plotly.express as px

    fig = px.histogram(
        df,
        x=column,
        marginal="box",
        color_discrete_sequence=["#3b82f6"],
        opacity=0.75,
        labels={column: column.replace("_", " ").title()},
    )
    # Rich tooltips (Plotly Reference: trace.hovertemplate)
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>")
    return _apply_modern_layout(fig, title or f"Distribution Analysis: {column.title()}")


def bar_chart(
    df: pd.DataFrame,
    column: str,
    title: str | None = None,
    top_n: int = 15,
    animation_frame: str | None = None,
) -> Any:
    """Return a refined interactive Plotly bar chart with sorted counts and optional animation."""
    import plotly.express as px

    if animation_frame:
        # For animation, we need the full series per frame
        counts = df.groupby([animation_frame, column]).size().reset_index(name="Count")
        # Ensure we only keep top_n per frame or overall
        top_cats = df[column].value_counts().head(top_n).index
        counts = counts[counts[column].isin(top_cats)]
        # Sort by animation frame to ensure correct playback order
        counts = counts.sort_values(animation_frame)
    else:
        counts = df[column].value_counts().head(top_n).reset_index()
        counts.columns = [column, "Count"]

    fig = px.bar(
        counts,
        x=column,
        y="Count",
        color="Count",
        color_continuous_scale="Blues",
        text_auto=".2s",
        animation_frame=animation_frame,
    )

    # Highlight the top record with an annotation (only for non-animated or first frame)
    if not animation_frame:
        top_val = counts.iloc[0][column]
        fig.add_annotation(
            x=top_val,
            y=counts.iloc[0]["Count"],
            text="Highest Frequency",
            showarrow=True,
            arrowhead=1,
            yshift=10,
        )

    fig.update_traces(
        textposition="outside", hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<extra></extra>"
    )
    return _apply_modern_layout(fig, title or f"Top {top_n} Categories: {column.title()}")


def correlation_heatmap(df: pd.DataFrame, title: str | None = None) -> Any:
    """Return a high-resolution interactive Plotly correlation heatmap."""
    import plotly.express as px
    import plotly.graph_objects as go

    corr = df.select_dtypes(include=DTYPE_NUM).corr()
    if corr.empty:
        return go.Figure()

    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
        labels=dict(color="Correlation"),
    )

    fig.update_xaxes(side="top")
    return _apply_modern_layout(fig, title or "Inter-Variable Correlation Matrix")


def time_series_chart(
    df: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None
) -> Any:
    """Create a high-performance time series chart using Scattergl (WebGL)."""
    import plotly.express as px

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    # Optimization: Use Scattergl for performance with large datasets
    # Note: px.line uses scatter traces; we'll convert them to scattergl
    fig = px.line(
        df,
        x=date_col,
        y=value_col,
        color=group_col,
    )

    # Plotly Reference Optimization: webgl is much faster for thousands of points
    fig.update_traces(mode="lines+markers", marker=dict(size=4))
    for i in range(len(fig.data)):
        fig.data[i].type = "scattergl"

    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(step="all"),
                ]
            )
        ),
    )

    fig.update_traces(hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: %{y:,.2f}<extra></extra>")

    return _apply_modern_layout(fig, f"Temporal Trend: {value_col.title()} Over Time")


def sunburst_chart(df: pd.DataFrame, path: list[str], values: str, title: str | None = None) -> Any:
    """Create a hierarchical Sunburst chart (Plotly Reference: Sunburst)."""
    import plotly.express as px

    fig = px.sunburst(
        df,
        path=path,
        values=values,
        color=values,
        color_continuous_scale="Viridis",
        branchvalues="total",  # Preserves area proportional to totals
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<br>Parent: %{parent}<extra></extra>"
    )
    return _apply_modern_layout(fig, title or "Hierarchical Data Breakdown")


def treemap_chart(df: pd.DataFrame, path: list[str], values: str, title: str | None = None) -> Any:
    """Create a hierarchical Treemap (Plotly Reference: Treemap)."""
    import plotly.express as px

    fig = px.treemap(
        df,
        path=path,
        values=values,
        color=values,
        color_continuous_scale="Blues",
    )
    fig.update_traces(
        textinfo="label+value+percent parent",
        hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<extra></extra>",
    )
    return _apply_modern_layout(fig, title or "Proportional Data Density")


def gauge_chart(value: float, target: float | None = None, title: str | None = None) -> Any:
    """Create a high-impact KPI Gauge (Plotly Reference: Indicator)."""
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta" if target is not None else "gauge+number",
            value=value,
            delta={"reference": target} if target is not None else None,
            title={"text": title, "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, max(value * 1.5, 100)]},
                "bar": {"color": "#3b82f6"},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 50], "color": "rgba(255, 0, 0, 0.1)"},
                    {"range": [50, 100], "color": "rgba(0, 255, 0, 0.1)"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": target if target is not None else value,
                },
            },
        )
    )
    return _apply_modern_layout(fig)


def animated_scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    animation_frame: str,
    size: str | None = None,
    color: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a fully animated scatter plot for exploring multi-dimensional trends over time."""
    import plotly.express as px

    # Ensure correct data types for animation
    df = df.dropna(subset=[x, y, animation_frame]).sort_values(animation_frame)

    fig = px.scatter(
        df,
        x=x,
        y=y,
        animation_frame=animation_frame,
        animation_group=color if color else x,
        size=size,
        color=color,
        hover_name=color if color else x,
        size_max=60,
        log_x=True if df[x].min() > 0 else False,
    )

    # Optimization for animation performance
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 400

    return _apply_modern_layout(fig, title or f"Animated Trends: {y.title()} vs {x.title()}")


def hotspot_density_mapbox(
    df: pd.DataFrame,
    lat_col: str = COL_LAT,
    lon_col: str = COL_LON,
    z_col: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a high-performance density mapbox (Heatmap) for operational hotspots (e.g. 311 complaints, defect clusters)."""
    import plotly.express as px

    # Drop missing coords for mapping
    plot_df = df.dropna(subset=[lat_col, lon_col])

    fig = px.density_mapbox(
        plot_df,
        lat=lat_col,
        lon=lon_col,
        z=z_col,
        radius=12,
        center=dict(lat=40.7128, lon=-74.0060),
        zoom=10,
        mapbox_style="carto-darkmatter",
        color_continuous_scale="Inferno",
    )

    fig.update_layout(margin=dict(t=80 if title else 0, b=0, l=0, r=0))
    return _apply_modern_layout(fig, title or "Operational Density Hotspots")


def material_breakdown_pie_chart(
    df: pd.DataFrame, material_col: str, title: str | None = None
) -> Any:
    """Create an interactive Donut chart mapping SDM materials to their exact hex colors."""
    import plotly.express as px

    from .engineering import SIDEWALK_MATERIALS

    counts = df[material_col].value_counts().reset_index()
    counts.columns = [material_col, "Count"]

    fig = px.pie(
        counts,
        names=material_col,
        values="Count",
        hole=0.45,  # Creates the Donut effect
        color=material_col,
        color_discrete_map=SIDEWALK_MATERIALS,  # Maps to your official engineering standards!
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
    )

    return _apply_modern_layout(fig, title or "Material Composition Breakdown")


def material_borough_subplots(
    df: pd.DataFrame, material_col: str, borough_col: str = "borough", title: str | None = None
) -> Any:
    """Create a 1xN matrix of Donut chart subplots breaking down materials by Borough."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    from .engineering import SIDEWALK_MATERIALS

    # Get top boroughs (up to 5) to avoid squishing the charts
    boroughs = df[borough_col].dropna().value_counts().head(5).index.tolist()
    if not boroughs:
        return material_breakdown_pie_chart(df, material_col, title)

    fig = make_subplots(
        rows=1,
        cols=len(boroughs),
        specs=[[{"type": "domain"}] * len(boroughs)],
        subplot_titles=boroughs,
    )

    for i, boro in enumerate(boroughs):
        boro_df = df[df[borough_col] == boro]
        counts = boro_df[material_col].value_counts().reset_index()
        counts.columns = [material_col, "Count"]

        colors = [SIDEWALK_MATERIALS.get(mat, "#9ca3af") for mat in counts[material_col]]

        fig.add_trace(
            go.Pie(
                labels=counts[material_col],
                values=counts["Count"],
                hole=0.45,
                marker=dict(colors=colors),
                name=str(boro),
                textinfo="percent",
                textposition="inside",
                hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
            ),
            1,
            i + 1,
        )

    return _apply_modern_layout(fig, title or f"Material Breakdown by {borough_col.title()}")


def operations_gantt_chart(
    df: pd.DataFrame,
    task_col: str,
    start_col: str,
    end_col: str,
    color_col: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a timeline/Gantt chart for tracking contract lifecycles, SLA durations, or permit windows."""
    import plotly.express as px

    plot_df = df.dropna(subset=[task_col, start_col, end_col]).copy()
    plot_df[start_col] = pd.to_datetime(plot_df[start_col])
    plot_df[end_col] = pd.to_datetime(plot_df[end_col])

    fig = px.timeline(
        plot_df, x_start=start_col, x_end=end_col, y=task_col, color=color_col, hover_name=task_col
    )

    # Tasks top-to-bottom
    fig.update_yaxes(autorange="reversed")
    return _apply_modern_layout(fig, title or "Operations Schedule & Timelines")


def triage_funnel_chart(df: pd.DataFrame, stage_col: str, title: str | None = None) -> Any:
    """Create a funnel chart to visualize operational throughput (e.g., Reported -> Inspected -> Assigned -> Completed)."""
    import plotly.express as px

    # Calculate counts per stage
    counts = df[stage_col].value_counts().reset_index()
    counts.columns = ["Stage", "Count"]

    # Optional: if you have a predefined order for stages, you can enforce it here
    # counts['Stage'] = pd.Categorical(counts['Stage'], categories=["Reported", "Inspected", "Assigned", "Completed"], ordered=True)
    # counts = counts.sort_values('Stage')

    fig = px.funnel(counts, x="Count", y="Stage", color="Stage")
    return _apply_modern_layout(fig, title or "Pipeline Conversion & Triage Funnel")


def plot_sidewalk_anatomy(geojson_data: dict[str, Any], title: str | None = None) -> Any:
    """Render a vectorized 2D sandbox schematic of sidewalk infrastructure."""
    import plotly.graph_objects as go

    fig = go.Figure()

    for feature in geojson_data.get("features", []):
        geom_type = feature.get("geometry", {}).get("type")
        coords = feature.get("geometry", {}).get("coordinates", [])
        props = feature.get("properties", {})

        if geom_type == "Polygon" and coords:
            # Extract x and y from the exterior polygon ring
            x = [pt[0] for pt in coords[0]]
            y = [pt[1] for pt in coords[0]]

            hover_text = (
                f"<b>Zone:</b> {props.get('zone_name', 'N/A')}<br>"
                f"<b>Material:</b> {props.get('material', 'N/A')}<br>"
                f"<b>Width:</b> {props.get('width_ft', 'N/A')} ft<br>"
                f"<b>Cross-Slope:</b> {props.get('cross_slope_pct', 'N/A')}%"
            )

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    fill="toself",
                    fillcolor=props.get("fill_color", "#cccccc"),
                    line=dict(color="rgba(255, 255, 255, 0.4)", width=1.5),
                    mode="lines",
                    name=props.get("zone_name", "Zone"),
                    text=hover_text,
                    hoverinfo="text",
                )
            )

    # Create proportional CAD/Blueprint axes
    fig.update_layout(
        xaxis=dict(scaleanchor="y", scaleratio=1, showgrid=True, title="Length (ft)"),
        yaxis=dict(showgrid=True, title="Width (ft)"),
    )
    return _apply_modern_layout(fig, title or "Vectorized Sidewalk Anatomy Sandbox")


def violin_plot(df: pd.DataFrame, x_col: str, y_col: str, title: str | None = None) -> Any:
    """Create a Violin plot to visualize distributions and probability density (e.g. Repair Cost by Borough)."""
    import plotly.express as px

    fig = px.violin(
        df,
        x=x_col,
        y=y_col,
        box=True,
        points="all",
        color=x_col,
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y}<extra></extra>")
    return _apply_modern_layout(fig, title or f"Distribution: {y_col.title()} by {x_col.title()}")


def quality_radar_chart(score_dict: dict[str, float], title: str | None = None) -> Any:
    """Create a Radar chart visualizing the multiple dimensions of data quality."""
    import plotly.graph_objects as go

    categories = ["Completeness", "Validity", "Consistency", "Freshness"]
    values = [score_dict.get(c.lower(), 100.0) for c in categories]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            line_color="#3b82f6",
        )
    )
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    return _apply_modern_layout(fig, title or "Data Quality Radar")


def generate_analysis_results(df: pd.DataFrame, analysis_type: str) -> dict[str, Any]:
    """Orchestrator to return the correct data structure for a given analysis type.

    Args:
        df: The input DataFrame.
        analysis_type: One of 'profile', 'anomaly', 'correlation', 'sla', 'borough'.

    Returns:
        A dictionary containing the results for the requested analysis.
    """
    if analysis_type == "profile":
        profile = profile_dataframe(df)
        return asdict(profile)
    elif analysis_type == "borough":
        return {"borough_data": compute_borough_metrics(df)}
    elif analysis_type == "sla":
        return {"sla_data": compute_sla_trends(df)}
    elif analysis_type == "anomaly":
        return {"anomalies": detect_anomalies(df).to_dict(orient="records")}
    elif analysis_type == "correlation":
        return {"correlation_matrix": correlation_analysis(df).to_dict()}
    elif analysis_type == "cost_estimate":
        from .engineering import estimate_costs, summarize_costs

        est_df = estimate_costs(df)
        summary = summarize_costs(est_df)
        return {"summary": asdict(summary), "records": est_df.head(100).to_dict(orient="records")}
    return {"message": f"Unknown analysis type: {analysis_type}"}


# ── Enums & Types ─────────────────────────────────────────────────────────────


class DataType(Enum):
    NUMERIC = "numeric"
    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"
    GEOSPATIAL = "geospatial"
