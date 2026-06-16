# NYC DOT SIM Toolkit — Interactive Jupyter Edition

Welcome to the **Sidewalk Inspection & Management (SIM) Toolkit** — an interactive Jupyter-based dashboard for analyzing NYC Open Data.

## What This Is

This is a fully interactive Jupyter Book with **the same functionality as the Dash Mission Control app**, including:

- **30+ interactive Plotly visualizations** — real-time charts, spatial maps, statistical analyses
- **Live Socrata data integration** — fetch fresh data from NYC Open Data
- **Interactive filters and controls** — dropdown, date range, borough selection
- **Advanced analytics** — Bayesian confidence intervals, spatial clustering, time-series forecasting
- **Quality scoring** — assess dataset freshness, completeness, validity
- **Spatial conflict detection** — intersection analysis, permit vs. inspection overlays

## Getting Started

### Option 1: Run Locally (Recommended)
```bash
# Install Jupyter Book and dependencies
pip install jupyter-book ipywidgets voila plotly

# Navigate to the book directory
cd jupyter_book

# Run as interactive Jupyter notebooks
jupyter notebook

# Or deploy as an interactive web app
voila dashboards/
```

### Option 2: Run in GitHub Pages
This book is deployed to GitHub Pages. Visit the live version:
📊 [NYC SIM Toolkit Interactive Dashboard](https://ryudkiss-hue.github.io/nyc_data)

## How It Works

Each dashboard is a **Jupyter notebook with ipywidgets controls**:

1. **Select your filters** — borough, date range, metrics, etc.
2. **Charts update in real-time** — Plotly visualizations respond to your selections
3. **See the data** — download tables, inspect raw data, export reports
4. **Run the code** — modify analyses, add your own calculations

## Dashboards

| Dashboard | Purpose |
|-----------|---------|
| **Inspection Dashboard** | Real-time overview of sidewalk inspection data, violations, and trends |
| **ADA Ramp Analysis** | Borough-level ramp completion rates with confidence intervals |
| **Spatial Conflict Detection** | Interactive map showing overlaps between permits and inspections |
| **Data Quality Scorecard** | Freshness, completeness, validity, consistency metrics for all 26 datasets |
| **Advanced Analytics** | CUSUM charts, Bayesian forecasting, KMeans clustering, survival analysis |

## Key Features

### Interactive Controls
```python
# Every dashboard includes:
- Borough selector (Manhattan, Bronx, Brooklyn, Queens, Staten Island)
- Date range picker
- Metric selector
- Data refresh button
```

### Live Data
All visualizations fetch data directly from **NYC Open Data (Socrata)** — you always get the freshest data.

Set your `SOCRATA_APP_TOKEN` environment variable for high-volume requests:
```bash
export SOCRATA_APP_TOKEN="your-token-here"
```

### Export & Download
Each chart includes:
- **Download as PNG/SVG** (Plotly toolbar)
- **Export as Excel** (table data)
- **Copy data as JSON** (for external analysis)

## Architecture

### Data Layer
```
NYC Open Data (Socrata API)
    ↓
DuckDB L2 Cache (Parquet)
    ↓
Pandas DataFrame
    ↓
Plotly Visualization
```

### Computation
- **Real-time filtering** — ipywidgets update controls instantly
- **Lazy evaluation** — data fetches only when you select new filters
- **Statistical computation** — Bayesian CIs, clustering, forecasting
- **Geospatial analysis** — shapely/geopandas intersection detection

## Dataset Registry

This book integrates **26 NYC Open Data datasets** across 4 categories:

### Core SIM Data (Inspection & Violations)
- `inspection` — 398K+ sidewalk inspection records (updates daily)
- `violations` — 312K+ violation records (updates daily)
- `dismissals` — 85K+ dismissed complaints (updates daily)
- `reinspection` — 36K+ follow-up results

### Accessibility (Ramps)
- `ramp_progress` — 187K+ active ramp entries (updates daily)
- `ramp_complaints` — 6K+ ramp complaints (updates daily)
- `ramp_locations` — 217K+ historical ramp data (stale since 2021)

### Coordination (Permits & Construction)
- `street_permits` — 3.6M permits with location and cost
- `street_construction_inspections` — 11.5M inspection records
- `street_resurfacing_schedule` — 309K+ scheduled paving projects
- ...and 8 more datasets

### Context Layers (Overlays)
- `complaints_311` — 21.3M 311 complaints
- `pedestrian_demand` — 127K pedestrian indicators
- `mappluto` — 858K property parcels
- ...and 3 more

## FAQ

**Q: How is this different from the Dash app?**
A: Same functionality, different medium. The Dash app is optimized for web deployment. This Jupyter Book is optimized for exploration, analysis, and education. You can modify the code directly in the notebooks.

**Q: Can I run this offline?**
A: Yes! Data is cached in Parquet format. See the Data Sources notebook for cache management.

**Q: How do I add my own analysis?**
A: Create a new `.ipynb` file in `dashboards/`, import the functions from `src/socrata_toolkit`, and add it to `_toc.yml`.

**Q: What if a dataset is stale?**
A: Each dashboard shows dataset freshness. Click "Refresh" to force a re-fetch. See PRODUCTION_READINESS.md for SLA details.

## CLI Toolkit

This book also documents the full **socrata CLI toolkit**:

```bash
# Dataset health
socrata dataset health --all --stale 7

# Fetch data
socrata fetch data.cityofnewyork.us dntt-gqwq --format xlsx

# Spatial analysis
socrata conflict-detect --borough MN --buffer 50

# Quality scoring
socrata quality-score data.cityofnewyork.us dntt-gqwq
```

See the **CLI Reference** section for 50+ commands.

## Support

- 📖 **Documentation** — See `docs/` folder in the repo
- 🐛 **Issues** — GitHub Issues on [nyc_data](https://github.com/ryudkiss-hue/nyc_data/issues)
- 💬 **Discussions** — GitHub Discussions for questions and ideas

## License

This project is provided under the MIT License. NYC Open Data is public domain.

---

**Ready to explore?** Pick a dashboard above and start filtering! 🗽📊
