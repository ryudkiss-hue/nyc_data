# Query Optimization Recommendations — {{query_name}}

**Generated:** {{report_date}}
**Engine:** {{engine}}
**Current runtime:** {{current_runtime}}
**Target runtime:** {{target_runtime}}

---

## Recommendations (Prioritized)

### 1. {{rec_1_title}} — Projected impact: {{rec_1_impact}}

**Current:**
```sql
{{rec_1_before}}
```

**Recommended:**
```sql
{{rec_1_after}}
```

**Why:** {{rec_1_rationale}}

---

### 2. {{rec_2_title}} — Projected impact: {{rec_2_impact}}

**Current:**
```sql
{{rec_2_before}}
```

**Recommended:**
```sql
{{rec_2_after}}
```

**Why:** {{rec_2_rationale}}

---

## NYC DOT-Specific Optimization Patterns

### DuckDB / Parquet (L2 Cache)

**Column pruning — always specify columns:**
```sql
-- Instead of SELECT * FROM cache
SELECT objectid, borough, status, inspection_date
FROM read_parquet('data/cache/inspection.parquet')
```

**Partition filtering — push predicates down:**
```sql
-- DuckDB can skip Parquet row groups when filtering on date
WHERE inspection_date >= '2026-01-01'::DATE
```

**Use hive partitioning if cache is partitioned by borough:**
```sql
FROM read_parquet('data/cache/violations/**/*.parquet', hive_partitioning=true)
WHERE borough = 'MN'
```

### Socrata SOQL

**Project only needed columns with $select:**
```
GET /resource/6kbp-uz6m.json?$select=objectid,borough,status,created_date&$limit=10000
```

**Combine $where + $group for server-side aggregation (avoids fetching raw rows):**
```
GET /resource/6kbp-uz6m.json?$select=borough,count(*)&$group=borough&$where=upper(borough)!='NULL'
```

**Use $offset for pagination instead of re-fetching all rows:**
```python
# Already handled by SocrataClient — pass max_rows and let client paginate
client.fetch_dataframe(domain, fourfour, max_rows=50000)
```

---

## Benchmarking Template

Run before and after applying recommendations to validate improvement:

```bash
time python -c "
import sys; sys.path.insert(0, 'src')
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', '{{fourfour}}', max_rows={{test_rows}})
print(f'Rows: {len(df)}, Cols: {len(df.columns)}')
"
```
