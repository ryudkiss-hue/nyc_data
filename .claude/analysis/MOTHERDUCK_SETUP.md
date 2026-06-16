# MotherDuck Setup Guide

Get your 26 NYC datasets on MotherDuck in 3 steps.

---

## Step 1: Create MotherDuck Account (2 min)

1. Visit: **https://console.motherduck.com/**
2. Sign up (free tier included)
3. Go to Account Settings → Generate Token
4. Copy your token (looks like: `md_...`)

---

## Step 2: Configure Token (1 min)

**Option A: Set environment variable**
```bash
export MOTHERDUCK_TOKEN="md_your_token_here"
echo 'export MOTHERDUCK_TOKEN="md_your_token_here"' >> ~/.bashrc
```

**Option B: Add to .env file**
```bash
# Edit .env
MOTHERDUCK_TOKEN=md_your_token_here
```

**Option C: Set in GitHub Actions (for CI/CD)**
```
Settings → Secrets and variables → Actions
Name: MOTHERDUCK_TOKEN
Value: md_your_token_here
```

---

## Step 3: Populate MotherDuck (25 min)

All 26 datasets from local Parquet cache → MotherDuck:

```bash
python .claude/analysis/optimized_motherduck_population.py
```

**Output:**
```
✓ inspection           399,424 rows      3.7MB  12.1s
✓ violations           312,828 rows     13.0MB  45.3s
✓ ramp_progress        187,023 rows      6.9MB  23.2s
...
Total: 26 tables in 24 minutes
```

---

## Verify Setup

```bash
# Python verification
python3 << 'EOF'
from socrata_toolkit.platform import get_connection, is_motherduck

if is_motherduck():
    print("✓ MotherDuck connected!")
    conn = get_connection()
    result = conn.execute("SELECT COUNT(*) as total FROM inspection").fetchall()
    print(f"✓ Inspection records: {result[0][0]:,}")
else:
    print("⚠️ Using DuckDB fallback")
EOF

# Or via CLI
duckdb "SELECT COUNT(*) FROM read_parquet('md:inspection')"
```

---

## Using MotherDuck

### In Python (Recommended)
```python
from socrata_toolkit.platform import get_connection

conn = get_connection()  # Automatically uses MotherDuck
df = conn.execute("SELECT * FROM inspection LIMIT 100").df()
```

### In Queries
```python
# Query ramp completion by borough
df = conn.execute("""
  SELECT borough, 
         COUNT(*) as total,
         SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
         ROUND(100.0 * SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct
  FROM ramp_progress
  GROUP BY borough
  ORDER BY pct DESC
""").df()
```

### Via Web Console
1. Visit: https://console.motherduck.com/
2. Click "SQL Editor"
3. Type your query:
   ```sql
   SELECT * FROM inspection LIMIT 10
   ```
4. Click Run

### Via DuckDB CLI
```bash
duckdb "SELECT COUNT(*) FROM read_parquet('md:violations')"
```

---

## Fallback to DuckDB

If MotherDuck is unavailable, code automatically falls back to local DuckDB:

```python
from socrata_toolkit.platform import get_connection, get_platform_name

conn = get_connection()  # Tries MotherDuck, falls back if needed
print(f"Using: {get_platform_name()}")  # Shows "motherduck" or "duckdb"

# Query works the same either way
df = conn.execute("SELECT * FROM inspection").df()
```

---

## Troubleshooting

**"MOTHERDUCK_TOKEN not set"**
```bash
# Check if token is set
echo $MOTHERDUCK_TOKEN

# If empty, set it:
export MOTHERDUCK_TOKEN="md_your_token"

# Verify (should show your token):
echo $MOTHERDUCK_TOKEN
```

**"Connection refused"**
- Check your internet connection
- Verify token is correct (copy from https://console.motherduck.com/)
- Try: `duckdb "SELECT 1"` to test

**"Query too slow"**
- Use WHERE filters to reduce data:
  ```sql
  SELECT * FROM complaints_311 
  WHERE created_date > CURRENT_DATE - 30
  ```
- For 21.3M row tables, always use filters

**Switch to DuckDB temporarily**
```python
# Force DuckDB (no MotherDuck)
conn = get_connection(platform='duckdb')
df = conn.execute("SELECT * FROM inspection").df()
```

---

## Cost

**Free Tier (Included):**
- 10 GB data transfer per month
- Unlimited queries
- Unlimited storage

**Paid Tier (Optional):**
- $0.08 per GB transferred (after 10GB free)
- Pay as you go

For 26 datasets (500MB Parquet):
- Initial upload: ~$0.02 (well within free tier)
- Monthly queries: ~$0.10-0.50 (unless doing massive exports)
- **Total: Free** (for most use cases)

---

## Next Steps

1. Create MotherDuck account
2. Set MOTHERDUCK_TOKEN in .env
3. Run population script
4. Start querying from Python or web console
5. (Optional) Invite team members to shared workspace

**All set! Your 26 datasets are now on MotherDuck.**

---

## Help

- MotherDuck Docs: https://motherduck.com/docs/
- DuckDB Docs: https://duckdb.org/docs/
- Check platform status: `python -c "from socrata_toolkit.platform import get_platform_name; print(get_platform_name())"`
