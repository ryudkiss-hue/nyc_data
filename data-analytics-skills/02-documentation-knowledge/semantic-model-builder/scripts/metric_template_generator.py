"""
Generate a YAML scaffold for a metric, dimension, or entity definition.

Usage:
    python metric_template_generator.py --type metric --name monthly_recurring_revenue
    python metric_template_generator.py --type dimension --name customer_segment
    python metric_template_generator.py --type entity --name customer --output entity.yaml
"""

import argparse
import sys
from datetime import date

METRIC_TEMPLATE = """\
# Metric definition — generated {date}
# Fill in all [REQUIRED] fields before committing.

metrics:
  - name: {name}
    description: "[REQUIRED] One sentence: what this metric measures and why it matters."
    label: "[REQUIRED] Human-readable label, e.g. 'Monthly Recurring Revenue'"
    type: simple  # simple | ratio | cumulative | derived
    type_params:
      measure:
        name: [REQUIRED]  # name of the underlying measure
        fill_nulls_with: 0  # or null
    filter: |
      # Optional: semantic layer filter expression
      # e.g. {{{{ Dimension('order__status') }}}} = 'completed'
    meta:
      owner: "[REQUIRED] team or person responsible for this metric"
      data_source: "[REQUIRED] source table(s)"
      grain: "[REQUIRED] e.g. one row per subscription per month"
      business_context: >
        [REQUIRED] Why does this metric exist? Who uses it?
        What decisions does it inform?
      calculation_notes: >
        [OPTIONAL] Edge cases, exclusions, known gotchas.
        e.g. "Excludes churned users; uses MRR at end of month, not daily average."
      good_value_range: "[OPTIONAL] e.g. > $1M = healthy; < $500K = at-risk"
      last_verified: {date}
"""

DIMENSION_TEMPLATE = """\
# Dimension definition — generated {date}

dimensions:
  - name: {name}
    label: "[REQUIRED] Human-readable label"
    description: "[REQUIRED] What this dimension represents"
    type: categorical  # categorical | time
    expr: "[REQUIRED] column name or SQL expression, e.g. customer_segment"
    meta:
      owner: "[REQUIRED]"
      possible_values:
        - "[OPTIONAL] list known values, e.g. 'enterprise', 'smb', 'consumer'"
      hierarchy:
        # For hierarchical dimensions (e.g. geography: country > region > city)
        - level: "[e.g. country]"
          column: "[column name]"
"""

ENTITY_TEMPLATE = """\
# Entity definition — generated {date}

entities:
  - name: {name}
    label: "[REQUIRED] Human-readable entity name"
    description: "[REQUIRED] What real-world object this entity represents"
    type: primary  # primary | foreign | unique | natural
    expr: "[REQUIRED] column name that identifies this entity, e.g. customer_id"
    meta:
      owner: "[REQUIRED]"
      source_table: "[REQUIRED] e.g. analytics.dim_customers"
      grain: "[REQUIRED] one row per ..."
      relationships:
        - entity: "[related entity name]"
          type: "one_to_many  # or many_to_one, many_to_many"
          join_key: "[foreign key column]"
"""

TEMPLATES = {
    "metric": METRIC_TEMPLATE,
    "dimension": DIMENSION_TEMPLATE,
    "entity": ENTITY_TEMPLATE,
}


def generate(object_type: str, name: str) -> str:
    template = TEMPLATES.get(object_type)
    if not template:
        raise ValueError(f"Unknown type: {object_type}. Choose from: {list(TEMPLATES.keys())}")
    return template.format(name=name, date=date.today().isoformat())


def main():
    parser = argparse.ArgumentParser(description="Generate a YAML scaffold for a semantic model object.")
    parser.add_argument("--type", required=True, choices=list(TEMPLATES.keys()),
                        help="Object type: metric, dimension, or entity")
    parser.add_argument("--name", required=True, help="Snake_case name for the object")
    parser.add_argument("--output", help="Optional output file path (default: print to stdout)")
    args = parser.parse_args()

    yaml_content = generate(args.type, args.name)

    if args.output:
        with open(args.output, "w") as f:
            f.write(yaml_content)
        print(f"Written to {args.output}")
    else:
        print(yaml_content)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("=== Demo: metric scaffold ===")
        print(generate("metric", "monthly_recurring_revenue"))
        print("\n=== Demo: entity scaffold ===")
        print(generate("entity", "customer"))
    else:
        main()
