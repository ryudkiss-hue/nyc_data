# NYC Open Data Registry Schema

## Overview

The **NYC Open Data Registry** is an authoritative, always-current JSON file containing complete metadata for all 3,000+ NYC Open Data datasets.

**File Location:** `pipeline/data/nyc_open_data_registry.json`  
**Auto-Generated:** Yes (syncs daily via `sync_socrata_config.py`)  
**Source of Truth:** Local Law 251 Inventory + Socrata API

---

## Structure

### Root Level
```json
{
  "metadata": { ... },
  "datasets": { ... },
  "index": { ... }
}
```

### Metadata Section
```json
"metadata": {
  "version": "1.0",
  "created_at": "2026-06-22T12:34:56.789Z",
  "last_synced": "2026-06-22T12:34:56.789Z",
  "total_datasets": 3012,
  "source": "Socrata API + Local Law 251 Inventory",
  "description": "Authoritative registry of all NYC Open Data datasets"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version |
| `created_at` | ISO datetime | When registry was first created |
| `last_synced` | ISO datetime | When last synced with Socrata |
| `total_datasets` | integer | Count of datasets in registry |
| `source` | string | Authority sources |
| `description` | string | Registry description |

### Datasets Section

```json
"datasets": {
  "6kbp-uz6m": {
    "socrata_id": "6kbp-uz6m",
    "name": "Sidewalk Management Database - Violations",
    "description": "Complete record of all sidewalk violations...",
    "agency": "Department of Transportation (DOT)",
    "category": "Transportation",
    "created_at": "2018-01-15",
    "last_updated": "2026-06-22T14:30:00.000Z",
    "update_frequency": "Daily",
    "row_count": 398451,
    "column_count": 42,
    "url": "https://data.cityofnewyork.us/d/6kbp-uz6m",
    "has_data_dictionary": true,
    "is_geocoded": "Yes",
    "visits": 15234,
    "downloads": 8901,
    "columns": [
      {
        "name": "Violation ID",
        "field_name": "violation_id",
        "datatype": "text",
        "description": "Unique identifier for violation record"
      },
      {
        "name": "Inspection Date",
        "field_name": "inspection_date",
        "datatype": "date",
        "description": "Date of sidewalk inspection"
      },
      ...
    ]
  },
  "dntt-gqwq": { ... },
  ...
}
```

#### Dataset Fields

| Field | Type | Description |
|-------|------|-------------|
| `socrata_id` | string | Unique Socrata identifier (4-letter code) |
| `name` | string | Official dataset name |
| `description` | string | Dataset description |
| `agency` | string | Responsible NYC agency |
| `category` | string | Data category (e.g., Transportation) |
| `created_at` | string | When dataset was published |
| `last_updated` | ISO datetime | When data was last refreshed |
| `update_frequency` | string | How often updated (Daily, Weekly, etc.) |
| `row_count` | integer | Number of rows in dataset |
| `column_count` | integer | Number of columns |
| `url` | string | Full NYC Open Data URL |
| `has_data_dictionary` | boolean | Whether data dictionary available |
| `is_geocoded` | string | Geographic coding status |
| `visits` | integer | Page view count |
| `downloads` | integer | Download count |
| `columns` | array | Complete column definitions |

#### Column Definition

```json
{
  "name": "Violation ID",
  "field_name": "violation_id",
  "datatype": "text",
  "description": "Unique identifier for violation record"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable column name |
| `field_name` | string | API field name (use in queries) |
| `datatype` | string | Data type (text, number, date, etc.) |
| `description` | string | Column description |

### Index Section

Provides fast lookup without scanning all datasets:

```json
"index": {
  "by_agency": {
    "Department of Transportation (DOT)": [
      "6kbp-uz6m",
      "dntt-gqwq",
      "gx72-kirf",
      ...
    ],
    "Department of Health and Mental Hygiene": [ ... ],
    ...
  },
  "by_keywords": {
    "sidewalk": ["6kbp-uz6m", "dntt-gqwq", ...],
    "inspection": ["6kbp-uz6m", "dntt-gqwq", ...],
    "violations": ["6kbp-uz6m", "agip-sqwc", ...],
    ...
  },
  "by_socrata_id": {
    "6kbp-uz6m": "6kbp-uz6m",
    "dntt-gqwq": "dntt-gqwq",
    ...
  }
}
```

---

## Usage Examples

### Python

```python
from app.initialization import get_registry

# Get registry
registry = get_registry()

# Get single dataset
violations = registry.get_dataset("6kbp-uz6m")
print(violations["description"])

# Filter by agency
dot_datasets = registry.filter_by_agency("Department of Transportation (DOT)")
print(f"Found {len(dot_datasets)} DOT datasets")

# Search by keyword
sidewalk_datasets = registry.search("sidewalk")
for ds in sidewalk_datasets:
    print(f"{ds['name']} - {ds['last_updated']}")

# Get all datasets
all_datasets = registry.get_all_datasets()
print(f"Total: {len(all_datasets)} datasets")

# Get raw registry (for export/backup)
full_registry = registry.get_registry_json()
```

### Access Columns

```python
registry = get_registry()
violations = registry.get_dataset("6kbp-uz6m")

# List all columns
for col in violations["columns"]:
    print(f"{col['name']} ({col['datatype']})")
    print(f"  Query field: {col['field_name']}")
    print(f"  Description: {col['description']}")
```

### Find Fresh Datasets

```python
from datetime import datetime, timedelta, timezone

registry = get_registry()
threshold = datetime.now(timezone.utc) - timedelta(days=7)

fresh_datasets = []
for ds in registry.get_all_datasets():
    last_updated = datetime.fromisoformat(ds["last_updated"].replace('Z', '+00:00'))
    if last_updated > threshold:
        fresh_datasets.append(ds)

print(f"Datasets updated in last 7 days: {len(fresh_datasets)}")
```

---

## Synchronization

### Automatic Sync
- Runs on app startup if last sync was > 1 day ago
- Checks Local Law 251 Inventory for updates
- Updates only changed datasets (efficient incremental sync)
- Takes ~30-60 seconds for full sync

### Manual Sync
```python
from app.initialization import sync_registry

sync_registry()  # Re-sync with Socrata
```

### Scheduled Sync (Daily)
```bash
# Add to crontab (run 2 AM daily)
0 2 * * * cd ~/Desktop/nyc_data && python pipeline/config/sync_socrata_config.py
```

---

## Integration Checklist

- [ ] Import `initialize_app` in `app/dash_app.py`
- [ ] Call `initialize_app()` before Dash runs
- [ ] Access registry via `get_registry()` in callbacks
- [ ] Use registry for dataset discovery
- [ ] Use column definitions for query building
- [ ] Monitor freshness via `last_updated` field

---

## Benefits

1. **Single Source of Truth** — All metadata flows from one authoritative registry
2. **Always Current** — Automatic daily sync keeps data fresh
3. **Complete Information** — All columns, metadata, and freshness info in one place
4. **Fast Lookup** — Indexed by agency, keyword, and Socrata ID
5. **Production Ready** — Used by pipeline, app, and all analysis tools

---

## Related Files

- `pipeline/data/nyc_open_data_registry.py` — Registry implementation
- `app/initialization.py` — App startup integration
- `pipeline/config/sync_socrata_config.py` — Daily sync script
- `pipeline/data/nyc_open_data_registry.json` — Generated registry file
