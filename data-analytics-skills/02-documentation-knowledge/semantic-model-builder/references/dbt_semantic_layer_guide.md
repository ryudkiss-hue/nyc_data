# dbt Semantic Layer Integration Guide — NYC DOT SIM

## Overview

The SIM semantic model YAML definitions are structured to be compatible with the
dbt Semantic Layer (MetricFlow). This guide covers how to adapt the generated
definitions for dbt projects targeting the Socrata/DuckDB data stack.

---

## Adapting metric_definition.yaml for dbt

dbt MetricFlow uses a slightly different YAML structure. Map SIM fields to dbt fields:

| SIM field | dbt MetricFlow field | Notes |
|---|---|---|
| `name` | `name` | Exact match — snake_case |
| `label` | `label` | Exact match |
| `description` | `description` | Exact match |
| `type` | `type` | Map: `simple` → `simple`, `ratio` → `ratio`, `cumulative` → `cumulative` |
| `model` | `type_params.measure.source_measure` | Use dbt model name |
| `numerator` | `type_params.numerator` | For ratio metrics |
| `denominator` | `type_params.denominator` | For ratio metrics |
| `dimensions` | `dimensions` (separate file) | Reference dimension names |
| `filters` | `filter` (jinja syntax) | Wrap in `{{ }}` for MetricFlow |

### Example: ramp_completion_rate in dbt format

```yaml
# models/marts/sim/metrics/ramp_completion_rate.yml
version: 2

metrics:
  - name: ramp_completion_rate
    label: Ramp Completion Rate
    description: >
      Percentage of curb ramps with status COMPLETE out of all non-cancelled ramps.
    type: ratio
    type_params:
      numerator: completed_ramps
      denominator: total_eligible_ramps
    filter: |
      {{ Dimension('ramp_progress__status') }} != 'CANCELLED'
    dimensions:
      - name: borough
      - name: fiscal_year
```

```yaml
# models/marts/sim/semantic_models/ramp_progress.yml
version: 2

semantic_models:
  - name: ramp_progress
    description: Curb ramp completion tracking (e7gc-ub6z)
    model: ref('stg_ramp_progress')
    defaults:
      agg_time_dimension: completion_date

    entities:
      - name: ramp
        type: primary
        expr: objectid

    measures:
      - name: completed_ramps
        description: Count of ramps with COMPLETE status
        agg: count
        expr: "CASE WHEN status = 'COMPLETE' THEN objectid END"

      - name: total_eligible_ramps
        description: Count of ramps excluding CANCELLED
        agg: count
        expr: "CASE WHEN status != 'CANCELLED' THEN objectid END"

    dimensions:
      - name: borough
        type: categorical
        expr: borough
      - name: fiscal_year
        type: time
        expr: "CASE WHEN MONTH(completion_date) >= 7 THEN YEAR(completion_date)+1 ELSE YEAR(completion_date) END"
        type_params:
          time_granularity: year
```

---

## Staging models for Socrata data

Since Socrata is the data source (not a warehouse with native dbt connectors), use
DuckDB Parquet cache files as the dbt source:

```yaml
# models/sources.yml
version: 2

sources:
  - name: socrata_cache
    description: L2 DuckDB Parquet cache of Socrata datasets
    database: "{{ env_var('DUCKDB_PATH', 'data/local_db/nyc_mission_control.duckdb') }}"
    schema: main
    tables:
      - name: inspection
        identifier: inspection_cache
        description: Sidewalk inspection records (dntt-gqwq)
        columns:
          - name: objectid
            description: Primary key
          - name: borough
            description: Borough code (MN/BX/BK/QN/SI)
          - name: status
          - name: inspection_date
          - name: created_date
          - name: unit_id
          - name: defect_type
          - name: material_type
          - name: the_geom

      - name: violations
        identifier: violations_cache
        description: Open sidewalk violations (6kbp-uz6m)

      - name: ramp_progress
        identifier: ramp_progress_cache
        description: Curb ramp completion tracking (e7gc-ub6z)
```

---

## Dimension configuration

Dimensions shared across multiple metrics must be defined once in a semantic model
and referenced by name in each metric. For SIM:

```yaml
# shared dimension block (included in each semantic model that uses borough)
dimensions:
  - name: borough
    type: categorical
    expr: borough
    # Valid values enforced at application layer, not dbt
```

---

## Validation workflow

1. Generate YAML with `scripts/semantic_model_generator.py --preset <name>`
2. Validate with `scripts/definition_validator.py --file <output>.yaml`
3. Copy validated content into dbt project under `models/marts/sim/`
4. Run `dbt parse` to check MetricFlow syntax
5. Run `dbt sl validate` (requires dbt Cloud or MetricFlow CLI)

---

## SIM-specific dbt conventions

- All SIM staging models are prefixed `stg_sim_` (e.g. `stg_sim_inspection`)
- Marts are under `models/marts/sim/`
- Metric definitions live in `models/marts/sim/metrics/`
- Semantic models live in `models/marts/sim/semantic_models/`
- Use `inspection_date` (not `created_date`) as the primary time dimension for inspection-based metrics
- Apply `WHERE status IN ('PASS', 'FAIL')` in staging for inspection pass rate to exclude pending records
