"""Validates semantic model YAML definitions for NYC DOT SIM metrics.

Checks required fields, type constraints, reference integrity, and
SIM-specific business rules.

Usage:
    python definition_validator.py --file metric_definition.yaml
    python definition_validator.py --file assets/metric_definition.yaml --strict
    python definition_validator.py --dir assets/ --type metric
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

KNOWN_MODELS = {
    "inspection",
    "violations",
    "ramp_progress",
    "dismissals",
    "ramp_complaints",
    "street_permits",
    "tree_damage",
    "ramp_locations",
    "lot_info",
    "sidewalk_planimetric",
    "complaints_311",
}

KNOWN_DIMENSIONS = {
    "borough",
    "defect_type",
    "material_type",
    "status",
    "inspection_month",
    "fiscal_year",
    "ramp_type",
}

KNOWN_METRIC_TYPES = {"simple", "ratio", "cumulative", "derived"}

REQUIRED_METRIC_FIELDS = {"name", "label", "description", "type", "model"}
REQUIRED_RATIO_FIELDS = {"numerator", "denominator"}
REQUIRED_SIMPLE_FIELDS = {"aggregation", "measure"}
REQUIRED_DIMENSION_FIELDS = {"name", "label", "type", "model", "column"}
REQUIRED_ENTITY_FIELDS = {"name", "label", "model", "primary_key"}

VALID_AGGREGATIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "MEDIAN"}
VALID_DIMENSION_TYPES = {"categorical", "time", "numeric"}
VALID_SLA_TIERS = {"HIGH", "MEDIUM", "LOW", None}
BOROUGH_CODES = {"MN", "BX", "BK", "QN", "SI"}


class ValidationError:
    def __init__(self, level: str, field: str, message: str):
        self.level = level  # ERROR | WARNING
        self.field = field
        self.message = message

    def __str__(self) -> str:
        return f"[{self.level}] {self.field}: {self.message}"


def _load_yaml(path: Path) -> dict:
    if not HAS_YAML:
        print("Error: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return yaml.safe_load(f) or {}


def validate_metric(m: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []

    # Required fields
    for field in REQUIRED_METRIC_FIELDS:
        if not m.get(field):
            errors.append(
                ValidationError("ERROR", field, f"Required field '{field}' is missing or empty.")
            )

    # Type-specific fields
    mtype = m.get("type", "")
    if mtype == "ratio":
        for field in REQUIRED_RATIO_FIELDS:
            if not m.get(field):
                errors.append(ValidationError("ERROR", field, f"Ratio metric requires '{field}'."))
    elif mtype == "simple":
        for field in REQUIRED_SIMPLE_FIELDS:
            if not m.get(field):
                errors.append(ValidationError("ERROR", field, f"Simple metric requires '{field}'."))
        agg = m.get("aggregation", "")
        if agg and agg.upper() not in VALID_AGGREGATIONS:
            errors.append(
                ValidationError(
                    "ERROR",
                    "aggregation",
                    f"'{agg}' is not a valid aggregation. Use: {', '.join(sorted(VALID_AGGREGATIONS))}",
                )
            )
    elif mtype and mtype not in KNOWN_METRIC_TYPES:
        errors.append(
            ValidationError(
                "ERROR",
                "type",
                f"'{mtype}' is not a known metric type. Use: {', '.join(KNOWN_METRIC_TYPES)}",
            )
        )

    # Model reference
    model = m.get("model", "")
    if model and model not in KNOWN_MODELS:
        errors.append(
            ValidationError(
                "WARNING",
                "model",
                f"'{model}' is not a known SIM dataset key. "
                f"Known: {', '.join(sorted(KNOWN_MODELS))}",
            )
        )

    # Dimension references
    for dim in m.get("dimensions", []):
        if dim not in KNOWN_DIMENSIONS:
            errors.append(
                ValidationError(
                    "WARNING",
                    "dimensions",
                    f"Dimension '{dim}' is not in the known SIM dimensions list. "
                    "Add it to dimension_definition.yaml if it's a new dimension.",
                )
            )

    # SLA tier
    sla = m.get("sla_tier")
    if sla and sla not in VALID_SLA_TIERS:
        errors.append(
            ValidationError(
                "WARNING", "sla_tier", f"'{sla}' is not a valid SLA tier. Use: HIGH, MEDIUM, LOW"
            )
        )

    # Description length
    desc = m.get("description", "")
    if len(desc) < 20:
        errors.append(
            ValidationError(
                "WARNING",
                "description",
                "Description is too short (< 20 chars). Provide a meaningful definition.",
            )
        )

    return errors


def validate_dimension(d: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for field in REQUIRED_DIMENSION_FIELDS:
        if not d.get(field):
            errors.append(
                ValidationError("ERROR", field, f"Required field '{field}' is missing or empty.")
            )

    dtype = d.get("type", "")
    if dtype and dtype not in VALID_DIMENSION_TYPES:
        errors.append(
            ValidationError(
                "ERROR",
                "type",
                f"'{dtype}' is not a valid dimension type. Use: {', '.join(VALID_DIMENSION_TYPES)}",
            )
        )

    model = d.get("model", "")
    if model and model not in KNOWN_MODELS:
        errors.append(
            ValidationError("WARNING", "model", f"'{model}' is not a known SIM dataset key.")
        )

    if d.get("name") == "borough" and d.get("type") == "categorical":
        valid_vals = set(d.get("valid_values", []))
        if valid_vals and not valid_vals.issubset(BOROUGH_CODES | {"UNKNOWN"}):
            errors.append(
                ValidationError(
                    "ERROR",
                    "valid_values",
                    f"Borough dimension has unexpected values: {valid_vals - BOROUGH_CODES}. "
                    "Expected: MN, BX, BK, QN, SI.",
                )
            )

    return errors


def validate_entity(e: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for field in REQUIRED_ENTITY_FIELDS:
        if not e.get(field):
            errors.append(
                ValidationError("ERROR", field, f"Required field '{field}' is missing or empty.")
            )

    model = e.get("model", "")
    if model and model not in KNOWN_MODELS:
        errors.append(
            ValidationError("WARNING", "model", f"'{model}' is not a known SIM dataset key.")
        )

    for ref in e.get("foreign_key_references", []):
        ref_ds = ref.get("dataset", "")
        if ref_ds and ref_ds not in KNOWN_MODELS:
            errors.append(
                ValidationError(
                    "WARNING",
                    "foreign_key_references",
                    f"Referenced dataset '{ref_ds}' is not in the known SIM registry.",
                )
            )

    return errors


def validate_file(path: Path, strict: bool = False) -> tuple[int, int]:
    doc = _load_yaml(path)
    all_errors: list[ValidationError] = []

    for m in doc.get("metrics", []):
        all_errors.extend(validate_metric(m))
    for d in doc.get("dimensions", []):
        all_errors.extend(validate_dimension(d))
    for e in doc.get("entities", []):
        all_errors.extend(validate_entity(e))

    if not any(key in doc for key in ("metrics", "dimensions", "entities")):
        print(f"WARNING: {path.name} has no metrics, dimensions, or entities sections.")

    error_count = sum(1 for e in all_errors if e.level == "ERROR")
    warn_count = sum(1 for e in all_errors if e.level == "WARNING")

    if all_errors:
        print(f"\n{path.name}:")
        for err in all_errors:
            print(f"  {err}")
    else:
        print(f"{path.name}: OK")

    if strict:
        error_count += warn_count

    return error_count, warn_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate NYC DOT SIM semantic model definitions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single YAML definition file")
    group.add_argument("--dir", help="Directory containing YAML definition files")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit non-zero on any warning)",
    )
    args = parser.parse_args()

    total_errors = 0
    total_warnings = 0

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: {path} not found.", file=sys.stderr)
            sys.exit(1)
        e, w = validate_file(path, strict=args.strict)
        total_errors += e
        total_warnings += w
    else:
        yaml_files = sorted(Path(args.dir).glob("*.yaml")) + sorted(Path(args.dir).glob("*.yml"))
        if not yaml_files:
            print(f"No YAML files found in {args.dir}")
            sys.exit(0)
        for yf in yaml_files:
            e, w = validate_file(yf, strict=args.strict)
            total_errors += e
            total_warnings += w

    print(f"\nSummary: {total_errors} error(s), {total_warnings} warning(s)")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
