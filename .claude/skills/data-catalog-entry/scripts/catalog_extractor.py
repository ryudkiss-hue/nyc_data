"""Data catalog extractor for NYC DOT Socrata datasets.

Pulls technical metadata (schema, row counts, sample values, null rates) from the
Socrata API and emits a structured catalog entry in YAML or Markdown format.

Usage:
    python catalog_extractor.py --key inspection
    python catalog_extractor.py --key violations --format yaml --out violations_catalog.yaml
    python catalog_extractor.py --key ramp_progress --format md --out ramp_catalog.md
    python catalog_extractor.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Known issues from CLAUDE.md for flagging in catalog entries
KNOWN_ISSUES: dict[str, str] = {
    "ramp_locations": "Stale since 2021. Use ramp_progress instead.",
    "weekly_construction": "Archived, no updates since 2017. Use street_construction_inspections.",
    "capital_blocks": "Empty dataset (0 rows). Use capital_intersections instead.",
    "permit_stipulations": "API returns HTTP 403. Contact NYC Open Data support.",
}

DATASET_REGISTRY: dict[str, dict] = {
    "inspection": {
        "fourfour": "dntt-gqwq",
        "rows": 398000,
        "update_freq": "daily",
        "sla": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
    "violations": {
        "fourfour": "6kbp-uz6m",
        "rows": 312000,
        "update_freq": "daily",
        "sla": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
    "ramp_progress": {
        "fourfour": "e7gc-ub6z",
        "rows": 187000,
        "update_freq": "daily",
        "sla": "HIGH",
        "owner": "NYC DOT Accessibility Programs",
    },
    "dismissals": {
        "fourfour": "p4u2-3jgx",
        "rows": 85000,
        "update_freq": "daily",
        "sla": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
    "ramp_complaints": {
        "fourfour": "jagj-gttd",
        "rows": 6000,
        "update_freq": "daily",
        "sla": "MEDIUM",
        "owner": "NYC DOT Accessibility Programs",
    },
    "street_permits": {
        "fourfour": "tqtj-sjs8",
        "rows": 3600000,
        "update_freq": "ongoing",
        "sla": "MEDIUM",
        "owner": "NYC DOT Permits",
    },
    "tree_damage": {
        "fourfour": "j6v2-6uxq",
        "rows": 17000,
        "update_freq": "irregular",
        "sla": "LOW",
        "owner": "NYC DOT SIM Unit",
    },
    "ramp_locations": {
        "fourfour": "ufzp-rrqu",
        "rows": 217000,
        "update_freq": "none",
        "sla": "LOW",
        "owner": "NYC DOT Accessibility Programs",
    },
    "lot_info": {
        "fourfour": "i642-2fxq",
        "rows": 1200000,
        "update_freq": "irregular",
        "sla": "LOW",
        "owner": "NYC DOT",
    },
    "sidewalk_planimetric": {
        "fourfour": "vfx9-tbb6",
        "rows": 50000,
        "update_freq": "irregular",
        "sla": "LOW",
        "owner": "NYC DOITT",
    },
    "complaints_311": {
        "fourfour": "erm2-nwe9",
        "rows": 21300000,
        "update_freq": "daily",
        "sla": "HIGH",
        "owner": "NYC 311",
    },
}

CORE_COLUMNS: dict[str, list[dict]] = {
    "inspection": [
        {
            "field": "objectid",
            "type": "number",
            "nullable": False,
            "description": "Unique inspection record identifier. Primary key.",
        },
        {
            "field": "borough",
            "type": "text",
            "nullable": True,
            "description": "Borough code. Values: MN, BX, BK, QN, SI. ~0.2% null.",
        },
        {
            "field": "status",
            "type": "text",
            "nullable": True,
            "description": "Inspection outcome. Common values: PASS, FAIL, PENDING.",
        },
        {
            "field": "inspection_date",
            "type": "calendar_date",
            "nullable": True,
            "description": "Date physical inspection was conducted (ISO 8601).",
        },
        {
            "field": "created_date",
            "type": "calendar_date",
            "nullable": True,
            "description": "Date record entered the system. Lags inspection_date by 0–45 days.",
        },
        {
            "field": "unit_id",
            "type": "text",
            "nullable": True,
            "description": "SIM unit identifier. Links to violations and dismissals datasets.",
        },
        {
            "field": "defect_type",
            "type": "text",
            "nullable": True,
            "description": "Classification of defect observed (CRACK, UNEVEN, OBSTRUCTION, etc.).",
        },
        {
            "field": "material_type",
            "type": "text",
            "nullable": True,
            "description": "Sidewalk material: CONCRETE, BRICK, ASPHALT, OTHER.",
        },
        {
            "field": "the_geom",
            "type": "point",
            "nullable": True,
            "description": "WGS84 lat/lon. Present on ~92% of records.",
        },
    ],
    "violations": [
        {
            "field": "objectid",
            "type": "number",
            "nullable": False,
            "description": "Unique violation record identifier. Primary key.",
        },
        {
            "field": "borough",
            "type": "text",
            "nullable": True,
            "description": "Borough code: MN, BX, BK, QN, SI.",
        },
        {
            "field": "status",
            "type": "text",
            "nullable": True,
            "description": "Violation status: OPEN, CLOSED, DISMISSED, IN PROGRESS.",
        },
        {
            "field": "created_date",
            "type": "calendar_date",
            "nullable": True,
            "description": "Date violation was issued.",
        },
        {
            "field": "unit_id",
            "type": "text",
            "nullable": True,
            "description": "SIM unit identifier. Foreign key to inspection.unit_id.",
        },
    ],
    "ramp_progress": [
        {
            "field": "objectid",
            "type": "number",
            "nullable": False,
            "description": "Unique ramp record identifier.",
        },
        {
            "field": "borough",
            "type": "text",
            "nullable": True,
            "description": "Borough code: MN, BX, BK, QN, SI.",
        },
        {
            "field": "status",
            "type": "text",
            "nullable": True,
            "description": "Ramp completion status: COMPLETE, PENDING, IN PROGRESS, CANCELLED.",
        },
        {
            "field": "the_geom",
            "type": "point",
            "nullable": True,
            "description": "Ramp location in WGS84. Present on ~88% of records.",
        },
    ],
}


def _fetch_live_metadata(key: str, registry_entry: dict) -> dict:
    fourfour = registry_entry["fourfour"]
    try:
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        meta = client.get_metadata("data.cityofnewyork.us", fourfour)
        return {
            "live": True,
            "last_modified": getattr(meta, "last_modified", None),
            "row_count": getattr(meta, "row_count", registry_entry["rows"]),
            "description": getattr(meta, "description", ""),
            "columns": meta.column_dict() if hasattr(meta, "column_dict") else [],
        }
    except Exception as exc:
        return {
            "live": False,
            "error": str(exc),
            "last_modified": None,
            "row_count": registry_entry["rows"],
            "description": "",
            "columns": CORE_COLUMNS.get(key, []),
        }


def _fetch_quality(key: str, fourfour: str) -> dict | None:
    try:
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig
        from socrata_toolkit.governance import compute_quality_score

        client = SocrataClient(SocrataConfig())
        df = client.fetch_dataframe("data.cityofnewyork.us", fourfour, max_rows=500)
        if df.empty:
            return None
        qs = compute_quality_score(df)
        return {
            "overall": round(qs.overall, 1),
            "completeness": round(qs.completeness, 1),
            "validity": round(qs.validity, 1),
            "consistency": round(qs.consistency, 1),
            "freshness": round(qs.freshness, 1),
            "sample_size": len(df),
        }
    except Exception:
        return None


def _build_catalog(key: str, include_quality: bool) -> dict:
    reg = DATASET_REGISTRY.get(key)
    if reg is None:
        print(
            f"Error: unknown dataset key '{key}'. Known keys: {', '.join(DATASET_REGISTRY)}",
            file=sys.stderr,
        )
        sys.exit(1)

    meta = _fetch_live_metadata(key, reg)
    quality = _fetch_quality(key, reg["fourfour"]) if include_quality else None

    columns = meta["columns"] or CORE_COLUMNS.get(key, [])
    # Normalise to dict format
    if columns and isinstance(columns[0], dict) and "fieldName" in columns[0]:
        columns = [
            {
                "field": c.get("fieldName", ""),
                "type": c.get("dataTypeName", ""),
                "nullable": True,
                "description": c.get("description", "")[:120],
            }
            for c in columns[:40]
        ]

    return {
        "catalog_entry": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_key": key,
            "fourfour": reg["fourfour"],
            "domain": "data.cityofnewyork.us",
            "owner": reg["owner"],
            "update_frequency": reg["update_freq"],
            "sla_tier": reg["sla"],
            "approximate_row_count": meta["row_count"],
            "last_modified": meta.get("last_modified"),
            "description": meta.get("description")
            or f"NYC DOT {key.replace('_', ' ').title()} dataset.",
            "live_metadata": meta["live"],
            "known_issues": KNOWN_ISSUES.get(key),
            "columns": columns,
            "quality_score": quality,
            "lineage": {
                "upstream": "NYC DOT SIM system → Socrata open data portal",
                "transformation": "None (raw open data)",
                "downstream_consumers": [],
            },
            "governance": {
                "sensitivity": "Public",
                "access_policy": "Open — no authentication required for <2K rows; "
                "SOCRATA_APP_TOKEN required for full corpus",
                "data_steward": reg["owner"],
                "review_cycle": "Annual",
            },
        }
    }


def _render_yaml(catalog: dict) -> str:
    import yaml

    return yaml.dump(catalog, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _render_md(catalog: dict) -> str:
    e = catalog["catalog_entry"]
    lines = [
        f"# Data Catalog Entry: `{e['dataset_key']}`",
        "",
        f"**Fourfour:** `{e['fourfour']}`  ",
        f"**Domain:** {e['domain']}  ",
        f"**Owner:** {e['owner']}  ",
        f"**Update frequency:** {e['update_frequency']}  ",
        f"**SLA tier:** {e['sla_tier']} (HIGH=14d / MEDIUM=30d / LOW=60d)  ",
        f"**Generated:** {e['generated_at'][:19]} UTC",
        "",
        "## Description",
        "",
        e["description"],
        "",
        "## Technical Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Approximate rows | {e['approximate_row_count']:,} |",
        f"| Last modified | {e.get('last_modified') or 'unknown'} |",
        f"| Live metadata | {'yes' if e['live_metadata'] else 'no (registry fallback)'} |",
        "",
    ]

    if e.get("known_issues"):
        lines += [
            "## Known Issues",
            "",
            f"> {e['known_issues']}",
            "",
        ]

    lines += ["## Schema", "", "| Field | Type | Nullable | Description |", "|---|---|---|---|"]
    for col in e.get("columns", []):
        nullable = "Yes" if col.get("nullable", True) else "No"
        lines.append(
            f"| `{col.get('field', '')}` | {col.get('type', '')} | {nullable} | "
            f"{col.get('description', '')[:100]} |"
        )

    lines.append("")

    if e.get("quality_score"):
        qs = e["quality_score"]
        lines += [
            "## Quality Score",
            "",
            f"Sample size: {qs.get('sample_size', '?')} rows",
            "",
            "| Dimension | Score |",
            "|---|---|",
            f"| **Overall** | **{qs['overall']}** |",
            f"| Completeness | {qs['completeness']} |",
            f"| Validity | {qs['validity']} |",
            f"| Consistency | {qs['consistency']} |",
            f"| Freshness | {qs['freshness']} |",
            "",
        ]

    lin = e["lineage"]
    gov = e["governance"]
    lines += [
        "## Lineage",
        "",
        f"**Upstream:** {lin['upstream']}  ",
        f"**Transformation:** {lin['transformation']}",
        "",
        "## Governance",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Sensitivity | {gov['sensitivity']} |",
        f"| Access policy | {gov['access_policy']} |",
        f"| Data steward | {gov['data_steward']} |",
        f"| Review cycle | {gov['review_cycle']} |",
    ]

    return "\n".join(lines)


def cmd_extract(args: argparse.Namespace) -> None:
    catalog = _build_catalog(args.key, include_quality=not args.no_quality)

    if args.format == "yaml":
        output = _render_yaml(catalog)
    elif args.format == "json":
        output = json.dumps(catalog, indent=2, default=str)
    else:
        output = _render_md(catalog)

    if args.out:
        Path(args.out).write_text(output)
        print(f"Written to: {args.out}")
    else:
        print(output)


def cmd_list(_args: argparse.Namespace) -> None:
    print(f"{'Key':<28} {'Fourfour':<12} {'Rows':>10} {'SLA':<8} {'Owner'}")
    print("-" * 80)
    for key, reg in DATASET_REGISTRY.items():
        issue = " [ISSUE]" if key in KNOWN_ISSUES else ""
        print(
            f"{key:<28} {reg['fourfour']:<12} {reg['rows']:>10,} "
            f"{reg['sla']:<8} {reg['owner']}{issue}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYC DOT data catalog extractor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Extract catalog entry for a dataset")
    p_extract.add_argument("--key", required=True, help="Dataset key (e.g. inspection)")
    p_extract.add_argument("--format", choices=["md", "yaml", "json"], default="md")
    p_extract.add_argument("--out", help="Output file path (default: stdout)")
    p_extract.add_argument(
        "--no-quality", action="store_true", help="Skip quality score computation (faster)"
    )

    sub.add_parser("list", help="List all known datasets")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "list":
        cmd_list(args)
