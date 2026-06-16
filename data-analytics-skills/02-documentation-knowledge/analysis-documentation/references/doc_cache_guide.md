# Analysis Documentation — Cache Configuration Guide

## Overview

`dynamic_doc_cache.py` generates structured markdown documentation for any registered
NYC Open Data dataset and caches the result in DuckDB. Cache behaviour is controlled
by `config/doc_cache_config.yaml`.

---

## Configuration file

Path: `config/doc_cache_config.yaml` (relative to project root)

```yaml
doc_cache:
  enabled: true
  cache_path: data/cache/doc_cache.duckdb
  invalidation_strategy: both   # ttl | content_hash | both
  ttl_hours: 24
  max_entries: 200
  audit_log: true

  auto_refresh:
    enabled: false
    refresh_before_expiry_hours: 2

  content:
    include_freshness: true
    include_row_count: true
    include_schema: true
    include_quality_score: true
    include_sample_queries: true
    max_sample_rows: 500        # rows fetched for quality scoring
```

---

## Invalidation strategies

| Strategy | When cache is invalidated | API calls on hit | Recommended for |
|---|---|---|---|
| `ttl` | After N hours regardless of upstream changes | 0 | Low-churn datasets (ramp_locations, step_streets) |
| `content_hash` | When dataset `last_modified` timestamp changes | 1 (metadata only) | Daily-update datasets (inspection, violations) |
| `both` | Whichever fires first | 0 or 1 | Default — all production use |

### How `content_hash` works

1. On each call, fetches `last_modified` from the Socrata metadata endpoint (1 lightweight call).
2. Computes SHA-256 over `(dataset_key, last_modified, content_config_flags)`.
3. If the hash differs from the stored value, the cached doc is stale and regenerated.

---

## Dataset registry

The generator reads `config/datasets.yaml` to resolve fourfour IDs and domain. If the
file is missing, the script falls back to the fourfour coded in the registry below.

| Key | Fourfour | Domain | Update frequency |
|---|---|---|---|
| inspection | dntt-gqwq | data.cityofnewyork.us | Daily |
| violations | 6kbp-uz6m | data.cityofnewyork.us | Daily |
| ramp_progress | e7gc-ub6z | data.cityofnewyork.us | Daily |
| dismissals | p4u2-3jgx | data.cityofnewyork.us | Daily |
| ramp_complaints | jagj-gttd | data.cityofnewyork.us | Daily |
| street_permits | tqtj-sjs8 | data.cityofnewyork.us | Ongoing |
| tree_damage | j6v2-6uxq | data.cityofnewyork.us | Irregular |

---

## CLI quick reference

```bash
# Generate (or return cached) doc for the inspection dataset
python scripts/dynamic_doc_cache.py --key inspection

# Force regeneration even if cache is fresh
python scripts/dynamic_doc_cache.py --key violations --invalidate

# List all cached entries with expiry and quality scores
python scripts/dynamic_doc_cache.py --list

# Clear the entire cache (use before schema migrations)
python scripts/dynamic_doc_cache.py --purge
```

---

## LRU eviction

When the cache exceeds `max_entries`, the oldest entries (by `generated_at`) are
evicted. Default is 200 entries — sufficient for all 26 registered datasets plus
repeated invalidations over several weeks.

---

## Audit logging

When `audit_log: true`, every cache hit and miss emits an `AuditLogger` event:

| Action | Trigger |
|---|---|
| `cache_hit` | Valid cached doc returned |
| `cache_miss` | No valid cache entry; doc generated |

Events are written to the governance audit trail. Disable with `audit_log: false`
in environments where governance logging is not needed (e.g. local dev).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Doc always shows stale timestamp | `ttl_hours` is too high | Lower `ttl_hours` or run with `--invalidate` |
| Quality score always `?` | Sample fetch fails (no token) | Set `SOCRATA_APP_TOKEN` env var |
| Cache DB locked | Another process has the DuckDB file open | Kill the other process or use a separate `cache_path` |
| Schema section missing | Dataset not in `datasets.yaml` | Add entry to `config/datasets.yaml` |
