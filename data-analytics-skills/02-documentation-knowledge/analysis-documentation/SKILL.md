# Skill: analysis-documentation

**Category:** Documentation & Knowledge  
**Trigger:** "Document this dataset", "generate analysis docs", "what does this dataset contain?"

---

## What this skill does

Generates structured, reproducible markdown documentation for any registered NYC Open Data dataset. Output covers description, schema, freshness, quality score, and sample queries.

Results are **cached in DuckDB** and served from cache on repeat calls. Cache invalidation is governed by `config/doc_cache_config.yaml`.

---

## Inputs

| Field | Required | Notes |
|---|---|---|
| `dataset_key` | Yes | Registry key (e.g. `inspection`, `violations`, `ramp_progress`) |
| `invalidate` | No | Force regeneration even if cache is fresh |

---

## Cache behaviour

Controlled by `config/doc_cache_config.yaml`:

| Setting | Default | Effect |
|---|---|---|
| `enabled` | `true` | Toggle caching on/off |
| `invalidation_strategy` | `both` | `ttl`, `content_hash`, or `both` |
| `ttl_hours` | `24` | Hours before a cached doc expires |
| `max_entries` | `200` | LRU eviction ceiling |
| `auto_refresh.enabled` | `false` | Background pre-refresh before expiry |
| `audit_log` | `true` | Emit AuditLogger events on cache hits/misses |

**Invalidation strategies:**
- `ttl` — expire after N hours regardless of data changes
- `content_hash` — expire when the dataset's `last_modified` timestamp changes (requires one metadata API call per invocation)
- `both` — expire on whichever condition fires first _(recommended)_

---

## Usage

```bash
# Generate (or return cached) docs for a dataset
python data-analytics-skills/04-documentation/analysis-documentation/scripts/dynamic_doc_cache.py \
    --key inspection

# Force regeneration
python ... --key inspection --invalidate

# List all cached entries
python ... --list

# Clear the entire cache
python ... --purge
```

```python
# Python API
from data_analytics_skills.analysis_documentation import get_or_generate

doc = get_or_generate("violations")
print(doc)
```

---

## Output format

```markdown
# Dataset Documentation: `inspection`
**Fourfour:** `dntt-gqwq`
**Generated:** 2026-06-05 01:30 UTC

## Description
...

## Freshness
**Last modified:** 2026-06-04T22:00:00

## Row Count
**Rows:** 398,412

## Schema
| Field | Type | Description |
...

## Quality Score
| Dimension | Score |
| Overall   | 87.4  |
...

## Sample Queries
...
```

---

## Common workflows

```
analysis-documentation → insight-synthesis          # doc → findings
analysis-documentation → data-quality-audit         # doc → deep QA
analysis-documentation → executive-summary-generator  # doc → exec brief
```

---

## Files

```
scripts/dynamic_doc_cache.py   — cache-backed doc generator (CLI + Python API)
```

Configuration: `config/doc_cache_config.yaml`  
Cache storage: `data/cache/doc_cache.duckdb` (default)
