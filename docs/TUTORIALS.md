# Tutorials — NYC DOT Sidewalk Toolkit

Step-by-step guides for common workflows using both the Dash dashboard and CLI.

---

## Tutorial 1: 5-Minute Dashboard Launch

**Goal:** Get Dash Mission Control running and explore sample data.  
**Time:** 5 minutes  
**Requirements:** Python 3.11+, pip, git

### Steps

#### 1. Clone and Install (2 minutes)

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
pip install -e ".[mission,xlsx]"
```

#### 2. Launch Dashboard (1 minute)

```bash
python app/dash_app.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8011
```

#### 3. Open in Browser (1 minute)

Navigate to: **http://localhost:8011**

#### 4. Explore (1 minute)

- **Home Tab** — View Metric cards and dataset health
- **Construction Tab** — Browse construction projects
- **GIS Tab** — View spatial maps and conflicts
- **Analytics Tab** — Advanced charts and metrics

#### 5. (Optional) Use Streamlit as Fallback (1 minute)

If you prefer the simplified UI:
```bash
streamlit run app/app.py
# → http://localhost:8501
```

### Success Indicators

✅ Dashboard loads at http://localhost:8011  
✅ Home tab shows Metric cards  
✅ GIS tab displays interactive map  
✅ Charts render without errors  

---

## Tutorial 2: Analyze Sidewalk Inspection Data

**Goal:** Fetch NYC sidewalk inspection data and generate a quality report.  
**Time:** 10 minutes  
**Prerequisites:** Completed Tutorial 1

### Steps

#### 1. Check Data Freshness (2 minutes)

```bash
socrata dataset health --key inspection
```

**Sample Output:**
```
Dataset: dntt-gqwq (inspections)
├─ Rows: 398,432
├─ Last update: 2026-06-16
├─ Age: 0 days ✅
├─ SLA threshold: 14 days
└─ Status: HEALTHY
```

#### 2. Profile the Data (3 minutes)

In the **Dash dashboard** (Home tab):
1. Click "Load Dataset: Inspections"
2. View completeness % and null rate breakdown
3. Check for duplicates and anomalies

Or via CLI:
```bash
socrata analyze data.cityofnewyork.us dntt-gqwq --profile
```

#### 3. Detect Anomalies (2 minutes)

```bash
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method isolation_forest \
  --out outliers.json
```

**Result:** JSON file with flagged anomalies (high/low outliers by column)

#### 4. Generate Quality Report (2 minutes)

In Dash dashboard (Data Quality tab):
1. View quality scorecard (0–100)
2. See completeness, validity, consistency, timeliness scores
3. Click "Export Report" → `quality_report.xlsx`

Or via CLI:
```bash
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --key-column id \
  --date-column created_date
```

#### 5. Check SLA Compliance (1 minute)

```bash
socrata observability sla-report --dataset dntt-gqwq
```

**Output:**
```
Dataset: dntt-gqwq (inspections)
├─ Last update: 2026-06-16 (0 days old)
├─ SLA threshold: 14 days
└─ Status: ✅ COMPLIANT
```

### Success Indicators

✅ Data freshness confirmed  
✅ Anomalies detected and exported  
✅ Quality score calculated  
✅ SLA compliance verified  

---

## Tutorial 3: Detect Spatial Conflicts (Permits vs. Inspections)

**Goal:** Find construction permits that overlap with sidewalk inspection sites.  
**Time:** 15 minutes  
**Prerequisites:** Tutorials 1–2

### Steps

#### 1. Launch Conflict Detection (2 minutes)

Via CLI:
```bash
socrata conflict-detect --borough MN --buffer 50 --output-format geojson --out conflicts.json
```

Via Dash:
1. Navigate to **GIS & Spatial** tab
2. Click "Conflict Buffer Overlay"
3. Select borough: **Manhattan (MN)**
4. Set buffer: **50 meters**
5. Click "Detect Conflicts"

#### 2. Analyze Results (5 minutes)

**Output Columns:**
- `permit_id` — Construction permit ID
- `inspection_id` — Overlapping inspection ID
- `distance_meters` — Distance between geometries
- `overlap_percent` — Overlap area percentage
- `severity` — High/Medium/Low (based on overlap %)

**Example Result:**
```json
{
  "permit_id": "201-456-789",
  "address": "150 E 42nd St, Manhattan",
  "inspection_id": "INS-987654",
  "distance_meters": 25,
  "overlap_percent": 35,
  "severity": "HIGH"
}
```

#### 3. Visualize on Map (5 minutes)

In Dash **GIS & Spatial** tab:
1. Conflicts appear as red circles (buffer zones)
2. Click on circle for details
3. Zoom to specific address
4. Toggle layers on/off

#### 4. Export Report (2 minutes)

```bash
# Export as GeoJSON for GIS software
socrata conflict-detect --all-boroughs \
  --output-format geojson \
  --out conflicts.geojson

# Export as Shapefile for ArcGIS
socrata conflict-detect --borough QN \
  --output-format shp \
  --out conflicts.shp
```

#### 5. Generate Management Report (1 minute)

```bash
socrata report contract --output conflict_management.xlsx
```

### Success Indicators

✅ Conflicts detected and exported  
✅ Map displays buffer zones  
✅ Severity levels calculated  
✅ Report generated for management  

---

## Tutorial 4: Track ADA Ramp Completion with Confidence Intervals

**Goal:** Analyze ramp completion rates by borough with statistical confidence.  
**Time:** 20 minutes  
**Prerequisites:** Tutorials 1–2

### Steps

#### 1. Sample Analysis (5 minutes)

```bash
socrata dataset ramp-analysis --sample 1000 --include-ci
```

**Sample Output:**
```
Borough | Total Ramps | Completed | Rate  | 95% CI         | N   | Reliability
--------|------------|-----------|-------|----------------|-----|----------
MN      | 145        | 87        | 60%   | [51%, 68%]    | 145 | HIGH
BX      | 98         | 52        | 53%   | [43%, 63%]    | 98  | MEDIUM
BK      | 212        | 118       | 56%   | [49%, 62%]    | 212 | HIGH
QN      | 176        | 89        | 51%   | [43%, 58%]    | 176 | HIGH
SI      | 67         | 31        | 46%   | [34%, 58%]    | 67  | MEDIUM
```

#### 2. Full-Corpus Analysis (10 minutes)

Requires `SOCRATA_APP_TOKEN`:
```bash
export SOCRATA_APP_TOKEN=your_token_here

socrata dataset ramp-analysis \
  --full-corpus \
  --include-ci \
  --all-boroughs
```

#### 3. Interpret Results (3 minutes)

**Key Metrics:**
- **Completion Rate** — % completed / total ramps
- **95% CI [lower, upper]** — Confidence interval (Wilson Score)
- **Reliability** — Based on sample size (n):
  - HIGH: n ≥ 100
  - MEDIUM: 50 ≤ n < 100
  - LOW: n < 50

**Example Interpretation:**
```
Manhattan: 60% completion rate [51%, 68%]
→ We're 95% confident the true completion rate is between 51–68%
→ Sample size = 145 (HIGH reliability)
→ Safe for decision-making
```

#### 4. Visualize in Dashboard (1 minute)

In Dash **Analytics** tab:
1. Select "Ramp Progress by Borough"
2. View confidence interval bars
3. Hover for exact numbers
4. Filter by date range if needed

#### 5. Track Over Time (1 minute)

```bash
# Export monthly trend
socrata analysis data.cityofnewyork.us e7gc-ub6z \
  --time-series created_date \
  --cohort-by borough \
  --metric completion_rate \
  --out ramp_trends.csv
```

### Success Indicators

✅ Completion rates calculated with CIs  
✅ Borough-level breakdown generated  
✅ Confidence intervals interpreted  
✅ Dashboard displays updated metrics  

---

## Tutorial 5: Query Data with Natural Language

**Goal:** Ask questions in English, get SQL results.  
**Time:** 10 minutes  
**Prerequisites:** Tutorials 1–2, `ANTHROPIC_API_KEY` set

### Steps

#### 1. Set Up API Key (1 minute)

```bash
export ANTHROPIC_API_KEY=your_claude_key_here
```

Get a key at: https://console.anthropic.com/

#### 2. Ask a Question (1 minute)

```bash
socrata nl-query \
  --dataset dntt-gqwq \
  "How many high-priority inspections by borough?"
```

**Behind the Scenes:**
1. Claude translates English → SOQL
2. SOQL runs against Socrata API
3. Results returned in table format

#### 3. More Examples (5 minutes)

```bash
# Question 1: Trends over time
socrata nl-query \
  --dataset dntt-gqwq \
  "Show me inspection count trend over last 30 days"

# Question 2: Statistical
socrata nl-query \
  --dataset e7gc-ub6z \
  "What percentage of ramps are completed in each borough?"

# Question 3: Filtering
socrata nl-query \
  --dataset 6kbp-uz6m \
  "List violations with 'DEFECTIVE' status from last week"

# Question 4: Complex aggregation
socrata nl-query \
  --dataset ugc8-s3f6 \
  "Average construction cost by project status and borough"
```

#### 4. Validate Before Running (2 minutes)

Use `--validate` flag to preview SOQL before execution:

```bash
socrata nl-query \
  --dataset dntt-gqwq \
  "Count by priority" \
  --validate
```

**Output:**
```
SOQL Generated:
SELECT priority, COUNT(*) AS count
FROM dntt-gqwq
GROUP BY priority
ORDER BY count DESC

Execute? [y/n]:
```

#### 5. Export Results (1 minute)

```bash
socrata nl-query \
  --dataset dntt-gqwq \
  "Top 10 locations by violation count" \
  --output json \
  > results.json

# Or use the Dashboard
# → Reports tab → Export to Excel
```

### Success Indicators

✅ English questions translated to SOQL  
✅ Results returned in seconds  
✅ Validations work before execution  
✅ Results exported to files/spreadsheets  

---

## Tutorial 6: Automate Daily Data Sync

**Goal:** Set up automated daily DuckDB cache refresh.  
**Time:** 20 minutes (one-time setup)  
**Prerequisites:** Linux/Mac or Windows with Task Scheduler

### Steps

#### 1. Create Sync Script (5 minutes)

```bash
# Create scripts/daily_sync.sh
cat > scripts/daily_sync.sh << 'EOF'
#!/bin/bash
export PYTHONPATH="src:."
export SOCRATA_APP_TOKEN="your_token_here"

# Sync primary datasets
socrata sync --dataset dntt-gqwq  # inspections
socrata sync --dataset 6kbp-uz6m  # violations
socrata sync --dataset e7gc-ub6z  # ramp_progress
socrata sync --dataset ugc8-s3f6  # built

# Check health
socrata dataset health --all --sort-by staleness

# Log results
echo "Daily sync completed at $(date)" >> data/logs/sync.log
EOF

chmod +x scripts/daily_sync.sh
```

#### 2. Test Manually (5 minutes)

```bash
./scripts/daily_sync.sh
```

**Expected Output:**
```
Syncing dntt-gqwq...
✓ 398,432 rows cached
Syncing 6kbp-uz6m...
✓ 312,156 rows cached
...
Daily sync completed at 2026-06-16 14:30:00
```

#### 3. Schedule on Linux/Mac (5 minutes)

Edit crontab:
```bash
crontab -e
```

Add entry for daily 2 AM sync:
```bash
0 2 * * * /home/user/nyc_data/scripts/daily_sync.sh
```

#### 4. Schedule on Windows (5 minutes)

Use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task → "Daily Data Sync"
3. Trigger: Daily @ 2:00 AM
4. Action: Start program
5. Program: `python`
6. Arguments: `scripts/daily_sync.sh` (via PowerShell)

Or create `scripts/daily_sync.ps1`:
```powershell
$env:PYTHONPATH = "src:."
$env:SOCRATA_APP_TOKEN = "your_token_here"

python -c "import subprocess; subprocess.run(['socrata', 'sync', '--dataset', 'dntt-gqwq'])"
# ... repeat for other datasets
```

#### 5. Monitor (Optional)

```bash
# Check sync status
tail -f data/logs/sync.log

# Verify DuckDB is updated
socrata db-status
```

### Success Indicators

✅ Sync script executes without errors  
✅ Data cached in DuckDB  
✅ Cron/Task Scheduler job created  
✅ Daily automated refresh working  

---

## Tutorial 7: Generate Monthly Report

**Goal:** Create executive summary with Metrics and visualizations.  
**Time:** 15 minutes  
**Prerequisites:** Tutorials 1–3

### Steps

#### 1. Gather Data (5 minutes)

```bash
# Contract performance
socrata report contract --output contract_report.xlsx

# Ramp completion
socrata report ramp --include-ci --output ramp_status.xlsx

# Inspection health
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --key-column id --date-column created_date > quality_metrics.txt
```

#### 2. Visualize Key Metrics (5 minutes)

In Dash **Dashboard** tab:
1. View Metric cards (top of page)
2. Click "Export to PDF"
3. Select metrics to include
4. Export as `monthly_dashboard.pdf`

#### 3. Create Executive Summary (3 minutes)

In Dash **Reports** tab:
1. Select report type: **Executive Summary**
2. Date range: **Last 30 days**
3. Include sections:
   - ✅ Inspection health
   - ✅ Construction progress
   - ✅ Ramp completion
   - ✅ Quality scorecard
4. Export → `monthly_summary.pptx`

#### 4. Compile in Office (2 minutes)

1. Open PowerPoint: `monthly_summary.pptx`
2. Add Excel charts from `contract_report.xlsx` and `ramp_status.xlsx`
3. Insert PDF export from step 2
4. Add executive summary text
5. Save as `Monthly_Report_June_2026.pptx`

### Success Indicators

✅ All reports generated  
✅ PDF/Excel/PPTX created  
✅ Metrics compiled  
✅ Ready to share with stakeholders  

---

## Troubleshooting Tips

### Dashboard Won't Load

```bash
# Check if port 8011 is in use
lsof -i :8011  # Linux/Mac
netstat -ano | findstr :8011  # Windows

# Kill process if needed
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Check logs
python app/dash_app.py --log-level DEBUG
```

### Data Sync Fails

```bash
# Verify API token
echo $SOCRATA_APP_TOKEN

# Test API connectivity
socrata search -q "inspection" --limit 1

# Check DuckDB
socrata db-status

# Rebuild cache
rm data/local_db/*.parquet
socrata sync --dataset dntt-gqwq --full-corpus
```

### CLI Commands Not Found

```bash
# Reinstall package
pip install -e ".[mission]" --force-reinstall

# Verify installation
which socrata
socrata --version

# Check Python path
python -c "import socrata_toolkit; print(socrata_toolkit.__file__)"
```

---

## Next Steps

- **Explore Dashboards:** All 7 tabs in Dash for complete workflows
- **Try Advanced Analytics:** Bayesian forecasting, KMeans clustering
- **Write Custom Analysis:** Extend `socrata_toolkit.analysis` with your own functions
- **Deploy to Cloud:** Use DEPLOYMENT_GUIDE.md for AWS/GCP/Azure

---

## Related Documentation

- [`QUICKSTART.md`](QUICKSTART.md) — 5-minute getting started
- [`CLI_REFERENCE.md`](CLI_REFERENCE.md) — Complete command reference
- [`MISSION_CONTROL.md`](MISSION_CONTROL.md) — Dashboard features
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — Production deployment
