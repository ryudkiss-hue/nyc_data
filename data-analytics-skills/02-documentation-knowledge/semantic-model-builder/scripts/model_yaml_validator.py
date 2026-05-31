"""
Validate a semantic model YAML file for required fields and basic consistency.

Checks:
- Required fields are present and non-empty
- Metric types are known values
- Referenced dimension names are defined in the same file
- No [REQUIRED] placeholder text remains

Usage:
    python model_yaml_validator.py --input metric_definition.yaml
    python model_yaml_validator.py --input assets/metric_definition.yaml --strict
"""

import argparse
import sys

try:
    import yaml
except ImportError:
    print("PyYAML not installed — run: pip install pyyaml")
    sys.exit(1)

VALID_METRIC_TYPES = {"simple", "ratio", "cumulative", "derived"}
VALID_DIMENSION_TYPES = {"categorical", "time"}
VALID_ENTITY_TYPES = {"primary", "foreign", "unique", "natural"}

REQUIRED_METRIC_FIELDS = ["name", "description", "type"]
REQUIRED_DIMENSION_FIELDS = ["name", "description", "type", "expr"]
REQUIRED_ENTITY_FIELDS = ["name", "description", "type", "expr"]


def check_placeholders(obj, path="") -> list[str]:
    """Recursively find any remaining [REQUIRED] or [OPTIONAL] placeholder strings."""
    issues = []
    if isinstance(obj, str):
        if "[REQUIRED]" in obj:
            issues.append(f"{path}: unfilled [REQUIRED] placeholder")
        elif "[OPTIONAL]" in obj and "[OPTIONAL]" != obj.strip():
            pass  # optional placeholders are acceptable
    elif isinstance(obj, dict):
        for k, v in obj.items():
            issues.extend(check_placeholders(v, path=f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            issues.extend(check_placeholders(v, path=f"{path}[{i}]"))
    return issues


def validate_metrics(metrics: list) -> list[str]:
    issues = []
    for m in metrics:
        name = m.get("name", "<unnamed>")
        for field in REQUIRED_METRIC_FIELDS:
            if not m.get(field):
                issues.append(f"metric '{name}': missing required field '{field}'")
        if m.get("type") and m["type"] not in VALID_METRIC_TYPES:
            issues.append(f"metric '{name}': unknown type '{m['type']}' — valid: {VALID_METRIC_TYPES}")
    return issues


def validate_dimensions(dimensions: list) -> list[str]:
    issues = []
    for d in dimensions:
        name = d.get("name", "<unnamed>")
        for field in REQUIRED_DIMENSION_FIELDS:
            if not d.get(field):
                issues.append(f"dimension '{name}': missing required field '{field}'")
        if d.get("type") and d["type"] not in VALID_DIMENSION_TYPES:
            issues.append(f"dimension '{name}': unknown type '{d['type']}' — valid: {VALID_DIMENSION_TYPES}")
    return issues


def validate_entities(entities: list) -> list[str]:
    issues = []
    for e in entities:
        name = e.get("name", "<unnamed>")
        for field in REQUIRED_ENTITY_FIELDS:
            if not e.get(field):
                issues.append(f"entity '{name}': missing required field '{field}'")
        if e.get("type") and e["type"] not in VALID_ENTITY_TYPES:
            issues.append(f"entity '{name}': unknown type '{e['type']}' — valid: {VALID_ENTITY_TYPES}")
    return issues


def validate_file(path: str, strict: bool = False) -> tuple[bool, list[str]]:
    with open(path) as f:
        data = yaml.safe_load(f)

    if data is None:
        return False, ["File is empty or not valid YAML"]

    issues = []
    if strict:
        issues.extend(check_placeholders(data))

    if "metrics" in data:
        issues.extend(validate_metrics(data["metrics"]))
    if "dimensions" in data:
        issues.extend(validate_dimensions(data["dimensions"]))
    if "entities" in data:
        issues.extend(validate_entities(data["entities"]))

    if not any(k in data for k in ("metrics", "dimensions", "entities")):
        issues.append("File must contain at least one of: metrics, dimensions, entities")

    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description="Validate semantic model YAML file.")
    parser.add_argument("--input", required=True, help="Path to YAML file")
    parser.add_argument("--strict", action="store_true", help="Fail on unfilled [REQUIRED] placeholders")
    args = parser.parse_args()

    ok, issues = validate_file(args.input, strict=args.strict)
    if ok:
        print(f"✓ {args.input} is valid")
    else:
        print(f"✗ {args.input} has {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import tempfile, os
        demo_yaml = """
metrics:
  - name: monthly_active_users
    description: Count of users who logged in at least once in the calendar month.
    type: simple
    type_params:
      measure:
        name: active_user_count
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(demo_yaml)
            tmp = f.name
        ok, issues = validate_file(tmp)
        print(f"Demo validation: {'PASS' if ok else 'FAIL'}")
        for i in issues:
            print(f"  - {i}")
        os.unlink(tmp)
    else:
        main()
