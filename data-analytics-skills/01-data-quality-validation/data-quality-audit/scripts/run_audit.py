#!/usr/bin/env python3
"""
run_audit.py — Comprehensive data quality audit for NYC DOT Socrata datasets.

Usage:
    python run_audit.py --key inspection --rows 10000
    python run_audit.py --key violations --rows 5000 --output audit_violations.md
    python run_audit.py --key ramp_progress --html --output audit_ramp.html
"""

import argparse
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, "src")

DATASET_KEYS = {
    "inspection": ("data.cityofnewyork.us", "dntt-gqwq"),
    "violations": ("data.cityofnewyork.us", "6kbp-uz6m"),
    "ramp_progress": ("data.cityofnewyork.us", "e7gc-ub6z"),
    "dismissals": ("data.cityofnewyork.us", "p4u2-3jgx"),
    "street_permits": ("data.cityofnewyork.us", "tqtj-sjs8"),
    "ramp_complaints": ("data.cityofnewyork.us", "jagj-gttd"),
}

# Business rules: (column, min, max) — None means no bound
RANGE_RULES = {
    "inspection": [
        ("inspection_date", "2000-01-01", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ],
    "violations": [
        ("created_date", "2000-01-01", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ],
    "ramp_progress": [
        ("inspection_date", "2000-01-01", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ],
}

REQUIRED_FIELDS = {
    "inspection": ["objectid", "borough", "status", "inspection_date"],
    "violations": ["objectid", "borough", "status", "created_date"],
    "ramp_progress": ["objectid", "borough", "status"],
    "dismissals": ["objectid", "borough"],
    "street_permits": ["permit_si_no", "borough", "work_type"],
    "ramp_complaints": ["unique_key", "borough"],
}

VALID_BOROUGHS = {
    "MN",
    "BX",
    "BK",
    "QN",
    "SI",
    "MANHATTAN",
    "BRONX",
    "BROOKLYN",
    "QUEENS",
    "STATEN ISLAND",
}


def fetch_data(key: str, rows: int) -> pd.DataFrame:
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    domain, fourfour = DATASET_KEYS[key]
    client = SocrataClient(SocrataConfig())
    print(f"Fetching {rows} rows from {key} ({fourfour})...")
    return client.fetch_dataframe(domain, fourfour, max_rows=rows)


def generate_demo_data() -> pd.DataFrame:
    """Synthetic NYC DOT inspection records for demo/offline use."""
    import random
    from datetime import date, timedelta

    random.seed(42)
    boroughs = ["MN", "BX", "BK", "QN", "SI", "INVALID_B"]
    statuses = ["OPEN", "CLOSED", "PENDING", "DISMISSED"]
    rows = []
    base = date(2025, 1, 1)
    for i in range(200):
        d = base + timedelta(days=random.randint(0, 500))
        rows.append(
            {
                "objectid": i if i != 5 else 4,  # one duplicate for dup check
                "borough": random.choices(boroughs, weights=[20, 20, 20, 20, 18, 2])[0],
                "status": random.choice(statuses),
                "inspection_date": str(d),
                "defect_count": random.randint(0, 15),
                "days_to_close": random.randint(1, 90) if random.random() > 0.2 else None,
            }
        )
    return pd.DataFrame(rows)


def check_completeness(df: pd.DataFrame, required: list[str]) -> dict:
    results = {}
    for col in df.columns:
        null_count = df[col].isna().sum()
        null_pct = null_count / len(df) * 100
        is_required = col in required
        severity = "ok"
        if null_pct > 5 and is_required:
            severity = "critical"
        elif null_pct > 10:
            severity = "major"
        elif null_pct > 1:
            severity = "minor"
        results[col] = {
            "null_count": int(null_count),
            "null_pct": round(null_pct, 2),
            "required": is_required,
            "severity": severity,
        }
    return results


def check_duplicates(df: pd.DataFrame, key_col: str = "objectid") -> dict:
    if key_col not in df.columns:
        return {"error": f"Key column '{key_col}' not present", "dup_count": 0, "dup_pct": 0.0}
    dup_count = df.duplicated(subset=[key_col]).sum()
    dup_pct = dup_count / len(df) * 100
    return {
        "key_column": key_col,
        "dup_count": int(dup_count),
        "dup_pct": round(dup_pct, 2),
        "severity": "critical" if dup_pct > 1 else ("major" if dup_pct > 0.1 else "ok"),
    }


def check_borough_validity(df: pd.DataFrame) -> dict:
    if "borough" not in df.columns:
        return {"error": "No 'borough' column"}
    invalid_mask = ~df["borough"].str.upper().isin(VALID_BOROUGHS) & df["borough"].notna()
    invalid_count = int(invalid_mask.sum())
    invalid_values = df.loc[invalid_mask, "borough"].value_counts().head(5).to_dict()
    return {
        "invalid_count": invalid_count,
        "invalid_pct": round(invalid_count / len(df) * 100, 2),
        "top_invalid_values": invalid_values,
        "severity": "critical" if invalid_count > 0 else "ok",
    }


def score_dimensions(completeness: dict, duplicates: dict, borough: dict) -> dict:
    required_cols = [v for v in completeness.values() if v["required"]]
    if required_cols:
        avg_null_pct = sum(v["null_pct"] for v in required_cols) / len(required_cols)
        completeness_score = max(0, 100 - avg_null_pct * 2)
    else:
        completeness_score = 100.0

    validity_score = 100.0 - borough.get("invalid_pct", 0) * 5
    validity_score = max(0, validity_score)

    dup_pct = duplicates.get("dup_pct", 0)
    consistency_score = max(0, 100 - dup_pct * 10)

    return {
        "completeness": round(completeness_score, 1),
        "validity": round(validity_score, 1),
        "consistency": round(consistency_score, 1),
        "overall": round(
            (completeness_score * 0.35 + validity_score * 0.25 + consistency_score * 0.25), 1
        ),
    }


def render_markdown(
    key: str, df: pd.DataFrame, completeness: dict, duplicates: dict, borough: dict, scores: dict
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Data Quality Audit — {key}",
        f"**Generated:** {now}  ",
        f"**Rows sampled:** {len(df):,}  ",
        f"**Columns:** {len(df.columns)}",
        "",
        "## Dimension Scores",
        "| Dimension | Score | Weight |",
        "|---|---|---|",
        f"| Completeness | {scores['completeness']}/100 | 35% |",
        f"| Validity | {scores['validity']}/100 | 25% |",
        f"| Consistency | {scores['consistency']}/100 | 25% |",
        f"| **Overall** | **{scores['overall']}/100** | — |",
        "",
        "## Completeness Detail",
        "| Column | Null % | Required | Severity |",
        "|---|---|---|---|",
    ]
    for col, v in sorted(completeness.items(), key=lambda x: -x[1]["null_pct"]):
        req = "yes" if v["required"] else "no"
        lines.append(f"| {col} | {v['null_pct']}% | {req} | {v['severity']} |")

    lines += [
        "",
        "## Duplicate Check",
        f"- Key column: `{duplicates.get('key_column', 'n/a')}`",
        f"- Duplicate rows: {duplicates.get('dup_count', 0):,} ({duplicates.get('dup_pct', 0)}%)",
        f"- Severity: **{duplicates.get('severity', 'ok')}**",
        "",
        "## Borough Validity",
        f"- Invalid borough values: {borough.get('invalid_count', 0):,} ({borough.get('invalid_pct', 0)}%)",
        f"- Severity: **{borough.get('severity', 'ok')}**",
    ]
    if borough.get("top_invalid_values"):
        lines.append("- Top invalid values:")
        for val, cnt in borough["top_invalid_values"].items():
            lines.append(f"  - `{val}`: {cnt}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="NYC DOT data quality audit")
    parser.add_argument(
        "--key",
        choices=list(DATASET_KEYS),
        help="Dataset key (required unless --demo is used)",
    )
    parser.add_argument("--demo", action="store_true", help="Run with synthetic demo data (no API)")
    parser.add_argument("--rows", type=int, default=5000, help="Rows to sample (default: 5000)")
    parser.add_argument("--output", default=None, help="Output file path (.md or .html)")
    parser.add_argument("--html", action="store_true", help="Output HTML report")
    args = parser.parse_args()

    if args.demo:
        df = generate_demo_data()
        key = "inspection"
        print("[INFO] Running with synthetic demo data (200 rows, inspection schema)")
    elif args.key:
        df = fetch_data(args.key, args.rows)
        key = args.key
    else:
        parser.error("--key or --demo is required")

    required = REQUIRED_FIELDS.get(key, [])

    completeness = check_completeness(df, required)
    duplicates = check_duplicates(df)
    borough = check_borough_validity(df)
    scores = score_dimensions(completeness, duplicates, borough)

    report = render_markdown(key, df, completeness, duplicates, borough, scores)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
