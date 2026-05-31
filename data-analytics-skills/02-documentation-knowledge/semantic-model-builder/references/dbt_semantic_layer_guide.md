# dbt Semantic Layer Guide

Reference for deploying metric and dimension YAML definitions to dbt Semantic Layer (MetricFlow). As of dbt 1.6+.

---

## File Structure

Place semantic model files in your dbt project alongside your models:

```
models/
├── marts/
│   └── core/
│       ├── fct_orders.sql
│       └── fct_orders.yml          # model config + semantic model definition
└── semantic_models/
    └── orders.yml                  # or separate semantic model files
```

---

## Semantic Model Definition

A semantic model connects a dbt model (or source) to the semantic layer. It defines measures, dimensions, and entities.

```yaml
semantic_models:
  - name: orders
    description: "Semantic model for order-level analytics."
    model: ref('fct_orders')        # the dbt model this is built on
    
    entities:
      - name: order
        type: primary
        expr: order_id
      - name: customer
        type: foreign
        expr: customer_id
    
    dimensions:
      - name: status
        type: categorical
        expr: order_status
      - name: created_at
        type: time
        expr: created_at
        type_params:
          time_granularity: day
    
    measures:
      - name: order_total
        description: "Sum of order amounts."
        agg: sum
        expr: order_amount
      - name: order_count
        description: "Count of distinct orders."
        agg: count_distinct
        expr: order_id
```

---

## Metric Definition

Metrics reference measures from semantic models. Define them in separate `metrics:` files or in the same file as the semantic model.

```yaml
metrics:
  - name: monthly_revenue
    label: "Monthly Revenue"
    description: "Total order revenue per month."
    type: simple
    type_params:
      measure:
        name: order_total         # must reference a measure defined above
    filter: |
      {{ Dimension('order__status') }} = 'completed'

  - name: conversion_rate
    label: "Conversion Rate"
    type: ratio
    type_params:
      numerator:
        name: converted_sessions
      denominator:
        name: total_sessions

  - name: cumulative_revenue
    label: "Cumulative Revenue (All Time)"
    type: cumulative
    type_params:
      measure:
        name: order_total
      window: all_time
```

---

## Metric Types in Detail

### Simple
Single measure, optionally filtered.
```yaml
type: simple
type_params:
  measure:
    name: order_count
    fill_nulls_with: 0
```

### Ratio
Two measures — numerator divided by denominator.
```yaml
type: ratio
type_params:
  numerator:
    name: paid_sessions
    filter: "{{ Dimension('session__is_paid') }} = true"
  denominator:
    name: total_sessions
```

### Cumulative
Running total from the start of the dataset or a defined window.
```yaml
type: cumulative
type_params:
  measure:
    name: revenue
  window: 30 days          # omit or set to 'all_time' for all-time cumulative
  grain_to_date: month     # alternative: cumulate within the current month only
```

### Derived
Arithmetic on other metrics (not measures).
```yaml
type: derived
type_params:
  expr: "revenue - cost"
  metrics:
    - name: revenue
    - name: cost
```

---

## Querying the Semantic Layer

CLI (dbt Cloud or local with dbt-metricflow):
```bash
mf query --metrics monthly_revenue --group-by metric_time__month
mf query --metrics conversion_rate --group-by customer__segment --start-time 2024-01-01
```

Validate definitions without querying:
```bash
mf validate-configs
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `measure not found` | Metric references a measure that doesn't exist in any semantic model | Check the measure name and semantic model file |
| `entity not found` | Dimension filter references an undefined entity | Verify entity is defined in the semantic model |
| `time spine missing` | Cumulative or offset metrics require a time spine model | Add `dbt_project.yml` time spine config and create the spine model |
| `ambiguous join path` | Two semantic models joined through multiple possible paths | Add explicit join constraints or split the query |

---

## Version Notes

- dbt Semantic Layer requires dbt Cloud (or dbt Core + MetricFlow SDK for local use)
- `type: derived` was introduced in dbt-metricflow 0.3 / dbt 1.7
- For dbt < 1.6, the legacy `metrics:` YAML block is used (different schema — consult dbt docs for that version)
