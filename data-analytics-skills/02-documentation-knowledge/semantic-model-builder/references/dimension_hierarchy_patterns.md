# Dimension Hierarchy Patterns

Dimensions categorise and slice metrics. This reference covers how to structure flat, hierarchical, and time dimensions in semantic models.

---

## Dimension Types

| Type | When to use | Example |
|---|---|---|
| **Categorical** | Discrete group labels | `customer_segment`, `country`, `product_line` |
| **Time** | Date/timestamp for time-series analysis | `signup_date`, `billing_month` |
| **Numeric** | Continuous value used as a filter or bucket | `age_band`, `revenue_tier` (after bucketing) |

---

## Flat Categorical Dimensions

A flat dimension has no hierarchical relationship between values — each value is independent.

```yaml
dimensions:
  - name: acquisition_channel
    type: categorical
    expr: acquisition_channel
    description: The marketing channel that drove the user's first session.
    meta:
      possible_values: [organic, paid_search, paid_social, email, referral, direct]
```

**Best practices:**
- Keep the value set documented in `possible_values`
- Use lowercase, underscore-separated values for consistency
- Define a fallback / unknown category rather than leaving nulls

---

## Hierarchical Dimensions

Use hierarchies when values have a parent-child relationship. Store each level as a separate column in the source table; reference them as a hierarchy in the dimension definition.

**Geography example:**
```
continent → country → region → city
```

```yaml
dimensions:
  - name: geography
    type: categorical
    expr: city  # leaf-level column used as the primary dimension
    description: Customer billing geography.
    meta:
      hierarchy:
        - level: continent
          column: billing_continent
        - level: country
          column: billing_country
        - level: region
          column: billing_region
        - level: city
          column: billing_city
```

**Product hierarchy example:**
```
category → subcategory → product_line → sku
```

**Time hierarchy example (see Time Dimensions section):**
```
year → quarter → month → week → day
```

---

## Time Dimensions

Time dimensions power time-series slicing. Always use a timestamp or date column as the source, not a pre-aggregated period string.

```yaml
dimensions:
  - name: created_at
    type: time
    expr: created_at
    description: Timestamp when the order was created (UTC).
    type_params:
      time_granularity: day  # smallest grain available
```

**Time granularity options:** `day`, `week`, `month`, `quarter`, `year`  
The semantic layer rolls up finer granularities automatically.

**Best practices:**
- Store all timestamps in UTC in the source table
- Use the finest granularity available (day or below); coarser grains are always derivable
- Avoid pre-computing `billing_month` as a string (YYYY-MM) — use a date column and let the layer truncate

---

## Slowly Changing Dimensions (SCDs)

When a dimension value changes over time (e.g. a customer changes their plan tier):

| Type | Behaviour | Use when |
|---|---|---|
| **SCD Type 1** | Overwrite — always shows current value | Historical values don't matter |
| **SCD Type 2** | Add a new row with `valid_from` / `valid_to` | Historical accuracy required |
| **SCD Type 3** | Add a `previous_value` column | Only one prior value matters |

For semantic models, SCD Type 2 is standard — join on `entity_id` and `event_date BETWEEN valid_from AND valid_to`.

---

## High-Cardinality Dimensions

Dimensions with thousands of distinct values (e.g. `company_name`, `product_sku`) cause performance problems in most BI tools.

**Strategies:**
1. **Bucket at ingestion:** convert `age` → `age_band` ('18-24', '25-34', etc.)
2. **Top-N + Other:** show top 20 values; collapse the rest into "Other"
3. **Search-based filter:** expose as a free-text filter rather than a dropdown
4. **Sub-dimension:** create a less granular parent dimension and only expose the leaf-level in drill-through
