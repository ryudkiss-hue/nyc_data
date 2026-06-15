"""Semantic model generator for NYC DOT SIM metrics and dimensions.

Generates dbt-compatible YAML metric definitions from structured inputs.
Supports metrics, dimensions, and entities for the SIM sidewalk inspection program.

Usage:
    python semantic_model_generator.py metric \\
        --name ramp_completion_rate \\
        --label "Ramp Completion Rate" \\
        --model ramp_progress \\
        --type ratio \\
        --numerator "count(case when status='COMPLETE' then 1 end)" \\
        --denominator "count(objectid)" \\
        --dimensions borough status \\
        --description "Percentage of curb ramps marked COMPLETE out of all non-cancelled ramps"

    python semantic_model_generator.py dimension \\
        --name borough \\
        --label "Borough" \\
        --model inspection \\
        --type categorical

    python semantic_model_generator.py entity \\
        --name sim_unit \\
        --label "SIM Inspection Unit" \\
        --model inspection \\
        --key unit_id

    python semantic_model_generator.py list-presets
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Pre-built metric presets for common SIM analytics
METRIC_PRESETS: dict[str, dict] = {
    "ramp_completion_rate": {
        "name": "ramp_completion_rate",
        "label": "Ramp Completion Rate",
        "description": "Percentage of curb ramps with status COMPLETE out of all "
        "non-cancelled ramps. Use Wilson Score CI when slicing by borough "
        "with n < 1000.",
        "type": "ratio",
        "model": "ramp_progress",
        "fourfour": "e7gc-ub6z",
        "numerator": "SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END)",
        "denominator": "COUNT(CASE WHEN status != 'CANCELLED' THEN 1 END)",
        "unit": "%",
        "grain": "borough, fiscal_year",
        "dimensions": ["borough", "fiscal_year", "ramp_type"],
        "filters": ["status != 'CANCELLED'"],
        "sla_tier": "HIGH",
        "owner": "NYC DOT Accessibility Programs",
    },
    "open_violation_count": {
        "name": "open_violation_count",
        "label": "Open Violation Count",
        "description": "Count of violation records with status = 'OPEN' at any point in time. "
        "Snapshot metric — point-in-time, not cumulative.",
        "type": "simple",
        "aggregation": "COUNT",
        "model": "violations",
        "fourfour": "6kbp-uz6m",
        "measure": "objectid",
        "unit": "count",
        "grain": "borough, week",
        "dimensions": ["borough", "defect_type", "material_type"],
        "filters": ["status = 'OPEN'"],
        "sla_tier": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
    "inspection_pass_rate": {
        "name": "inspection_pass_rate",
        "label": "Inspection Pass Rate",
        "description": "Percentage of inspections resulting in a PASS outcome. "
        "Excludes PENDING and NULL status records.",
        "type": "ratio",
        "model": "inspection",
        "fourfour": "dntt-gqwq",
        "numerator": "SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END)",
        "denominator": "COUNT(CASE WHEN status IN ('PASS', 'FAIL') THEN 1 END)",
        "unit": "%",
        "grain": "borough, month",
        "dimensions": ["borough", "defect_type", "material_type", "inspection_month"],
        "filters": ["status IN ('PASS', 'FAIL')", "inspection_date IS NOT NULL"],
        "sla_tier": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
    "avg_violation_age_days": {
        "name": "avg_violation_age_days",
        "label": "Average Open Violation Age (Days)",
        "description": "Mean number of days between created_date and current date "
        "for violations with status = 'OPEN'. Measures backlog recency.",
        "type": "simple",
        "aggregation": "AVG",
        "model": "violations",
        "fourfour": "6kbp-uz6m",
        "measure": "DATEDIFF('day', created_date, CURRENT_DATE)",
        "unit": "days",
        "grain": "borough, snapshot_date",
        "dimensions": ["borough", "defect_type"],
        "filters": ["status = 'OPEN'"],
        "sla_tier": "HIGH",
        "owner": "NYC DOT SIM Unit",
    },
}

DIMENSION_PRESETS: dict[str, dict] = {
    "borough": {
        "name": "borough",
        "label": "Borough",
        "description": "NYC borough code. Values: MN (Manhattan), BX (Bronx), "
        "BK (Brooklyn), QN (Queens), SI (Staten Island).",
        "type": "categorical",
        "model": "inspection",
        "column": "borough",
        "valid_values": ["MN", "BX", "BK", "QN", "SI"],
        "null_handling": "Exclude from borough breakdowns; include in city-wide totals as UNKNOWN",
    },
    "defect_type": {
        "name": "defect_type",
        "label": "Defect Type",
        "description": "Classification of sidewalk defect observed during inspection.",
        "type": "categorical",
        "model": "inspection",
        "column": "defect_type",
        "valid_values": ["CRACK", "UNEVEN", "OBSTRUCTION", "TREE_DAMAGE", "OTHER"],
        "null_handling": "Exclude from defect breakdowns",
    },
}

ENTITY_PRESETS: dict[str, dict] = {
    "sim_unit": {
        "name": "sim_unit",
        "label": "SIM Inspection Unit",
        "description": "A uniquely identified sidewalk segment tracked by the SIM program. "
        "unit_id links inspection, violations, and dismissals datasets.",
        "model": "inspection",
        "primary_key": "unit_id",
        "foreign_key_references": [
            {"dataset": "violations", "fourfour": "6kbp-uz6m", "column": "unit_id"},
            {"dataset": "dismissals", "fourfour": "p4u2-3jgx", "column": "unit_id"},
        ],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_yaml(obj: dict) -> str:
    if HAS_YAML:
        return yaml.dump(obj, allow_unicode=True, sort_keys=False, default_flow_style=False)
    # Fallback: simple JSON-like output
    import json

    return json.dumps(obj, indent=2, default=str)


def cmd_metric(args: argparse.Namespace) -> None:
    if args.preset:
        if args.preset not in METRIC_PRESETS:
            print(
                f"Error: unknown preset '{args.preset}'. Available: {', '.join(METRIC_PRESETS)}",
                file=sys.stderr,
            )
            sys.exit(1)
        definition = METRIC_PRESETS[args.preset].copy()
    else:
        if not all([args.name, args.model, args.type]):
            print(
                "Error: --name, --model, and --type are required without --preset.", file=sys.stderr
            )
            sys.exit(1)
        definition = {
            "name": args.name,
            "label": args.label or args.name.replace("_", " ").title(),
            "description": args.description or "",
            "type": args.type,
            "model": args.model,
            "dimensions": args.dimensions or [],
            "filters": args.filters or [],
            "unit": args.unit or "",
            "grain": args.grain or "",
            "owner": args.owner or "NYC DOT SIM Unit",
        }
        if args.type == "ratio":
            definition["numerator"] = args.numerator or ""
            definition["denominator"] = args.denominator or ""
        else:
            definition["aggregation"] = args.aggregation or "COUNT"
            definition["measure"] = args.measure or "objectid"

    output = {
        "version": 2,
        "generated_at": _now(),
        "metrics": [definition],
    }

    out_path = Path(args.out) if args.out else None
    content = _dump_yaml(output)
    if out_path:
        out_path.write_text(content)
        print(f"Written metric definition to: {out_path}")
    else:
        print(content)


def cmd_dimension(args: argparse.Namespace) -> None:
    if args.preset:
        definition = DIMENSION_PRESETS.get(args.preset)
        if not definition:
            print(
                f"Error: unknown preset '{args.preset}'. Available: {', '.join(DIMENSION_PRESETS)}",
                file=sys.stderr,
            )
            sys.exit(1)
        definition = definition.copy()
    else:
        definition = {
            "name": args.name,
            "label": args.label or args.name.replace("_", " ").title(),
            "description": args.description or "",
            "type": args.type or "categorical",
            "model": args.model,
            "column": args.column or args.name,
        }

    output = {"version": 2, "generated_at": _now(), "dimensions": [definition]}
    content = _dump_yaml(output)
    if args.out:
        Path(args.out).write_text(content)
        print(f"Written dimension definition to: {args.out}")
    else:
        print(content)


def cmd_entity(args: argparse.Namespace) -> None:
    if args.preset:
        definition = ENTITY_PRESETS.get(args.preset)
        if not definition:
            print(f"Error: unknown preset '{args.preset}'.", file=sys.stderr)
            sys.exit(1)
        definition = definition.copy()
    else:
        definition = {
            "name": args.name,
            "label": args.label or args.name.replace("_", " ").title(),
            "description": args.description or "",
            "model": args.model,
            "primary_key": args.key,
        }

    output = {"version": 2, "generated_at": _now(), "entities": [definition]}
    content = _dump_yaml(output)
    if args.out:
        Path(args.out).write_text(content)
        print(f"Written entity definition to: {args.out}")
    else:
        print(content)


def cmd_list_presets(_args: argparse.Namespace) -> None:
    print("METRIC PRESETS")
    for name, m in METRIC_PRESETS.items():
        print(f"  {name:<35} {m['label']} ({m['model']}, {m.get('unit', '')})")
    print("\nDIMENSION PRESETS")
    for name, d in DIMENSION_PRESETS.items():
        print(f"  {name:<35} {d['label']} ({d['type']})")
    print("\nENTITY PRESETS")
    for name, e in ENTITY_PRESETS.items():
        print(f"  {name:<35} {e['label']} (key: {e['primary_key']})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYC DOT SIM semantic model generator")
    sub = parser.add_subparsers(dest="command", required=True)

    # metric
    pm = sub.add_parser("metric", help="Generate a metric definition")
    pm.add_argument("--preset", choices=list(METRIC_PRESETS))
    pm.add_argument("--name")
    pm.add_argument("--label")
    pm.add_argument("--model", help="Source dbt model / dataset key")
    pm.add_argument("--type", choices=["simple", "ratio", "cumulative", "derived"])
    pm.add_argument("--aggregation", choices=["COUNT", "SUM", "AVG", "MIN", "MAX"])
    pm.add_argument("--measure")
    pm.add_argument("--numerator")
    pm.add_argument("--denominator")
    pm.add_argument("--dimensions", nargs="+")
    pm.add_argument("--filters", nargs="+")
    pm.add_argument("--unit")
    pm.add_argument("--grain")
    pm.add_argument("--description")
    pm.add_argument("--owner")
    pm.add_argument("--out", help="Output YAML file path")

    # dimension
    pd = sub.add_parser("dimension", help="Generate a dimension definition")
    pd.add_argument("--preset", choices=list(DIMENSION_PRESETS))
    pd.add_argument("--name")
    pd.add_argument("--label")
    pd.add_argument("--model")
    pd.add_argument("--type", choices=["categorical", "time", "numeric"])
    pd.add_argument("--column")
    pd.add_argument("--description")
    pd.add_argument("--out")

    # entity
    pe = sub.add_parser("entity", help="Generate an entity definition")
    pe.add_argument("--preset", choices=list(ENTITY_PRESETS))
    pe.add_argument("--name")
    pe.add_argument("--label")
    pe.add_argument("--model")
    pe.add_argument("--key", help="Primary key column name")
    pe.add_argument("--description")
    pe.add_argument("--out")

    sub.add_parser("list-presets", help="List all built-in presets")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    {
        "metric": cmd_metric,
        "dimension": cmd_dimension,
        "entity": cmd_entity,
        "list-presets": cmd_list_presets,
    }[args.command](args)
