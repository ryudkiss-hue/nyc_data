# NYC DOT SIM Toolkit — Interactive Jupyter Book

An interactive Jupyter-based dashboard with **the same functionality as the Dash Mission Control app**.

## Quick Start

### Option 1: Run Locally (Recommended)

```bash
# Install dependencies (if not already installed)
pip install jupyter jupyterlab ipywidgets plotly voila

# Navigate to the book directory
cd jupyter_book

# Launch Jupyter
jupyter notebook

# Then visit http://localhost:8888 and open any dashboard notebook
```

### Option 2: Run as Interactive Web App (Voila)

```bash
# Install voila
pip install voila

# Run from the dashboards directory
cd jupyter_book/dashboards
voila .

# Visit http://localhost:8866 to see the interactive app
```

### Option 3: Deploy to GitHub Pages

See [Deployment Guide](#deployment-guide) below.

---

## Dashboards

This book includes **5 core interactive dashboards** matching the Dash app:

| Dashboard | Purpose | Interactivity |
|-----------|---------|---|
| **01 - Inspection Dashboard** | Real-time overview of sidewalk inspections | Borough/date filters, real-time charts |
| **02 - ADA Ramp Analysis** | Ramp completion rates with confidence intervals | Borough selection, Wilson Score CIs |
| **03 - Spatial Conflict Detection** | Permit vs. inspection location overlap | Interactive map, distance analysis |
| **04 - Quality Scorecard** | Data quality metrics (completeness, validity, timeliness) | Heatmap, radar charts, summary table |
| **05 - Advanced Analytics** | CUSUM, Bayesian, K-Means clustering | Statistical visualizations |

### Reference Sections

- **Dataset Registry** — Catalog of 26 NYC Open Data datasets with freshness status
- **CLI Reference** — Complete command reference for the `socrata` CLI toolkit

---

## Features

### Interactive Controls
Each notebook includes:
- **ipywidgets** for filtering (dropdowns, date pickers, sliders)
- **Plotly** for interactive visualizations
- **Live data fetching** from NYC Open Data via Socrata API
- **Export buttons** (CSV, Excel, JSON)

### Data Integration
All notebooks fetch live data from **NYC Open Data** unless offline. Set your API token:

```bash
export SOCRATA_APP_TOKEN="your-token-here"
```

### No Setup Required
- Works in Jupyter, JupyterLab, or Voila
- Fallback to sample data if API unavailable
- All dependencies specified in `requirements-dev.txt`

---

## File Structure

```
jupyter_book/
├── intro.md                           # Welcome & overview
├── dashboards/
│   ├── 01_inspection_dashboard.ipynb  # Main inspection analysis
│   ├── 02_ramp_analysis.ipynb         # ADA ramp completion rates
│   ├── 03_gis_overview.ipynb          # Spatial conflict detection
│   ├── 04_quality_scorecard.ipynb     # Data quality assessment
│   └── 05_advanced_analytics.ipynb    # Statistical analyses
├── reference/
│   ├── dataset_registry.md            # 57 datasets catalog
│   └── cli_reference.md               # CLI toolkit commands
├── _config.yml                        # Jupyter Book config
├── _toc.yml                           # Table of contents
└── README.md                          # This file
```

---

## Deployment Guide

### Deploy to GitHub Pages

#### Step 1: Install Build Dependencies
```bash
pip install jupyter-book ghp-import
```

#### Step 2: Build the Static Site
```bash
cd /home/user/nyc_data/jupyter_book

# Execute notebooks and build HTML
jupyter-book build . \
  --execute \
  --execute-kernel python3 \
  --output-format html
```

#### Step 3: Deploy to GitHub Pages
```bash
# Push the built site to gh-pages branch
ghp-import -n -p -f _build/html
```

The site will be available at: `https://ryudkiss-hue.github.io/nyc_data/jupyter_book/`

### Alternative: Deploy via GitHub Actions

Create `.github/workflows/jupyter-book-deploy.yml`:

```yaml
name: Deploy Jupyter Book

on:
  push:
    branches:
      - main
    paths:
      - 'jupyter_book/**'
      - '.github/workflows/jupyter-book-deploy.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -q jupyter-book ghp-import
          pip install -r requirements-dev.txt
      
      - name: Build Jupyter Book
        run: |
          cd jupyter_book
          jupyter-book build . --execute --output-format html
      
      - name: Deploy to GitHub Pages
        run: |
          cd jupyter_book
          ghp-import -n -p -f _build/html
```

---

## Running Notebooks

### In Jupyter
1. Launch: `jupyter notebook`
2. Open any `.ipynb` file from the `dashboards/` folder
3. Run cells with `Shift+Enter`
4. Adjust filters in ipywidgets cells
5. Charts update instantly

### In Voila (Web App Mode)
```bash
cd jupyter_book/dashboards
voila 01_inspection_dashboard.ipynb
# Opens at http://localhost:8866
```

### In VS Code
- Install the "Jupyter" extension
- Open any `.ipynb` file
- Run cells directly in the editor

---

## Tips & Tricks

### Speed Up Execution
```python
# Set this in any cell to use cached data
import os
os.environ['SOCRATA_CACHE_DIR'] = '/data/cache'
os.environ['DUCKDB_PATH'] = '/data/local_db/nyc_mission_control.duckdb'
```

### Modify a Dashboard
1. Open the notebook in Jupyter
2. Edit cells as needed
3. Add new visualizations or analyses
4. Save and re-run cells

### Add a New Dashboard
1. Create a new file: `dashboards/06_my_analysis.ipynb`
2. Add it to `_toc.yml` under the `chapters:` section
3. Run locally to test
4. Commit and push (will auto-deploy if using GitHub Actions)

### Export Data
Each notebook includes export buttons:
- **CSV** — Open in Excel or Python
- **Excel** — Ready for reports
- **JSON** — Import to other tools

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'dash'"
→ Notebooks fallback to sample data if dependencies are missing. Run `pip install -r requirements-dev.txt` to get full functionality.

### "Socrata API error"
→ Check your `SOCRATA_APP_TOKEN`: `echo $SOCRATA_APP_TOKEN`
→ Notebooks automatically use sample data if API is unavailable.

### Plots not showing in Jupyter Lab
→ Run: `jupyter labextension enable @jupyterlab/plotly-extension`

### Voila app too slow
→ Voila executes cells on-demand. Pre-execute notebooks or enable caching:
```bash
voila --enable_nbconvert=True 01_inspection_dashboard.ipynb
```

---

## FAQ

**Q: Can I export these as a PDF report?**  
A: Yes! In Jupyter, use File → Export As → PDF via LaTeX. Or use `nbconvert`:
```bash
jupyter nbconvert --to pdf dashboards/01_inspection_dashboard.ipynb
```

**Q: Can I share a notebook with someone else?**  
A: Yes! Send the `.ipynb` file. They can open it in Jupyter or view it on GitHub (which renders notebooks).

**Q: How do I update the data?**  
A: Click the "Refresh Data" button in any dashboard. Or manually:
```python
df = fetch_inspection_data()  # Re-fetches from Socrata
```

**Q: Can I automate dashboard generation?**  
A: Yes! Use `nbconvert` to execute notebooks programmatically:
```bash
jupyter nbconvert --to html --execute dashboards/01_inspection_dashboard.ipynb
```

---

## Related Resources

- **Dash Mission Control** — Run `python app/dash_app.py` for the primary app
- **CLI Toolkit** — Run `socrata --help` for command-line analysis
- **Documentation** — See `docs/` folder for complete guides
- **GitHub** — https://github.com/ryudkiss-hue/nyc_data

---

**Next Steps:**
1. Run a notebook locally: `jupyter notebook dashboards/01_inspection_dashboard.ipynb`
2. Explore the interactive filters
3. Export data or modify charts
4. Deploy to GitHub Pages (see Deployment Guide above)



