# Socrata API Token Setup Guide

This guide walks you through configuring live data access from NYC Open Data.

## Quick Start

### 1. Get a Free Socrata API Token

1. Visit: https://data.cityofnewyork.us/profile/developer_settings
2. Sign up for a free NYC Open Data account (if you don't have one)
3. Generate an API token
4. Copy the token to your clipboard

### 2. Configure the Token

**Option A: Using .env file (recommended)**

```bash
# Copy the template
cp .env.example .env

# Edit .env and replace the placeholder
nano .env
# Change: SOCRATA_APP_TOKEN=your-socrata-app-token-here
# To:     SOCRATA_APP_TOKEN=YOUR_ACTUAL_TOKEN_HERE

# Verify the configuration
python scripts/verify_socrata_config.py
```

**Option B: Using environment variable**

```bash
export SOCRATA_APP_TOKEN=YOUR_ACTUAL_TOKEN_HERE
python scripts/verify_socrata_config.py
```

**Option C: Using Docker**

```bash
docker run -e SOCRATA_APP_TOKEN=YOUR_ACTUAL_TOKEN_HERE \
           -p 8501:8501 mission-control
```

## Verification

Run the configuration verification script:

```bash
python scripts/verify_socrata_config.py
```

Expected output for configured token:
```
✓ SOCRATA_APP_TOKEN configured: YOUR_TOKEN_PART...
✓ Connected to Socrata API (NYC Open Data)
✓ Retrieved metadata for dataset: Pedestrian Ramp - Program Progress
✓ Fetched 5 sample rows
✓ DuckDB cache available: /tmp/socrata_cache
✓ All checks passed! System is ready for production.
```

## What Token Does

With a **Socrata API token**, you get:

| Feature | Without Token | With Token |
|---------|---------------|-----------|
| Public Dataset Access | ✓ Yes | ✓ Yes |
| Rate Limit | 1,000 req/day | 50,000 req/day |
| Full-Corpus Fetch | ✗ No (2K sample) | ✓ Yes (50K+) |
| Authentication | No | Yes |

### Example: Full-Corpus Ramp Analysis

```bash
# Without token: fetches 100-2000 sample rows
socrata dataset ramp-analysis --sample 100

# With token: fetches all 50K+ rows with confidence intervals
socrata dataset ramp-analysis --full-corpus --borough MN
```

## Common Operations

### Verify Data is Live

```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
import os

# Check token
token = os.getenv('SOCRATA_APP_TOKEN')
print(f"Token configured: {bool(token and token != 'your-socrata-app-token-here')}")

# Fetch live data
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe(
    domain='data.cityofnewyork.us',
    fourfour='e7gc-ub6z',  # Ramp Progress dataset
    max_rows=100
)
print(f"Fetched {len(df)} rows, last updated {datetime.utcnow()}")
```

### Check Dataset Health

```bash
# Show all datasets with staleness and row counts
socrata dataset health --all --sort-by staleness

# Show only stale datasets (>14 days)
socrata dataset health --stale 14

# Show only empty datasets
socrata dataset health --empty
```

### Analyze Borough Completion Rates

```bash
# Quick analysis (100 sample rows)
socrata dataset ramp-analysis --sample 100

# Full statistical analysis (all 50K+ rows, requires token)
socrata dataset ramp-analysis --full-corpus --include-ci --borough MN
```

## Troubleshooting

### "SOCRATA_APP_TOKEN not set"

Your token is not configured. Follow the setup steps above.

```bash
# Check current token
echo $SOCRATA_APP_TOKEN

# If empty, add to .env
echo "SOCRATA_APP_TOKEN=YOUR_TOKEN_HERE" >> .env
```

### "No SOCRATA_APP_TOKEN; falling back to unauthenticated access"

Your token is not configured. The toolkit still works with public data but has lower rate limits.

```bash
# Verify full configuration
python scripts/verify_socrata_config.py
```

### "HTTP 429: Too Many Requests"

You've exceeded the rate limit for unauthenticated access (1,000 req/day). Configure a token to get 50,000 req/day.

### "Dataset not found" for e7gc-ub6z

The ramp progress dataset may have been moved. Check available datasets:

```bash
socrata search "ramp" --limit 5
```

## Environment Variables Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SOCRATA_APP_TOKEN` | No | (none) | API token from NYC Open Data profile |
| `SOCRATA_DOMAIN` | No | data.cityofnewyork.us | Socrata domain (can change for testing) |
| `SOCRATA_CACHE_DIR` | No | /tmp/socrata_cache | Location for L2 DuckDB cache |
| `ANTHROPIC_API_KEY` | No | (none) | For natural language queries |
| `SLACK_WEBHOOK_URL` | No | (none) | For alert notifications |

## Resources

- **API Documentation**: https://dev.socrata.com/
- **NYC Open Data**: https://data.cityofnewyork.us/
- **Socrata SDK Docs**: https://github.com/xmunoz/sodapy
- **Community Support**: https://discourse.socrata.com/

## Example: Complete Setup

```bash
# 1. Clone the repository
git clone https://github.com/ryudkiss-hue/nyc_data
cd nyc_data

# 2. Create .env with your token
cp .env.example .env
nano .env  # Add your SOCRATA_APP_TOKEN

# 3. Install dependencies
pip install -e ".[mission]"
pip install -r requirements-dev.txt

# 4. Verify configuration
python scripts/verify_socrata_config.py

# 5. Start using live data
streamlit run app/app.py
# or
socrata dataset health --all
# or
socrata dataset ramp-analysis --full-corpus --borough MN
```

---

**Last Updated**: 2026-06-02  
**Status**: ✓ Production Ready with Live Data
