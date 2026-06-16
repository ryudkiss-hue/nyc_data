# Learnings Log: Interactive Jupyter Notebooks at Scale

**Capture Date:** 2026-06-16  
**Project:** Jupyter Book with Dash app parity  
**Category:** Interactive data dashboards, deployment patterns  
**Applicability:** Any multi-notebook project with GitHub Actions deployment

---

## Core Patterns

### 1. **ipywidgets + Plotly for Interactive Dashboards**

**Pattern:**
```python
import ipywidgets as widgets
import plotly.graph_objects as go

# Create controls
borough_filter = widgets.Dropdown(
    options=['All', 'MANHATTAN', 'BRONX', ...],
    description='Borough:'
)

# Create visualization (re-renders on filter change)
def update_plot(borough):
    df_filtered = df[df['borough'] == borough] if borough != 'All' else df
    fig = go.Figure(...)
    fig.show()

# Bind control to visualization
widgets.interactive(update_plot, borough=borough_filter)
```

**Why it works:**
- ipywidgets are lightweight (no backend needed)
- Plotly figures are interactive by default
- Works in Jupyter, JupyterLab, and Voila
- Users can modify code directly

**When to use:**
- Data exploration dashboards (< 100K rows)
- Educational/analytical notebooks
- Offline-capable tools

**Avoid when:**
- Real-time streaming data (>1K updates/sec)
- Very large datasets (>1M rows) without caching
- Requires complex backend logic

---

### 2. **Graceful API Fallback Pattern**

**Pattern:**
```python
def fetch_data(api_endpoint, fallback_generator):
    """Fetch live or return sample data."""
    try:
        return api.fetch(endpoint, timeout=5)
    except (ConnectionError, TimeoutError, APIError):
        print(f"ℹ Using sample data (API unavailable)")
        return fallback_generator()
```

**Why it works:**
- Users never hit errors; notebooks always work
- Enables offline exploration
- Good for demos and testing
- Production data is real; sample data is realistic

**Checklist:**
- ✅ Sample data has same schema as live data
- ✅ Sample data uses realistic distributions (not uniform)
- ✅ Error message is helpful (not silent)
- ✅ Live vs. sample clearly indicated in output

**Example:**
```python
df = fetch_inspection_data(
    api='https://data.cityofnewyork.us/api',
    fallback_generator=lambda: generate_sample_inspection_data(n=5000)
)
```

---

### 3. **Notebook Structure for Data Dashboards**

**Standard sections (in order):**

1. **Setup** — imports, path setup, suppress warnings
2. **Controls** — ipywidgets definitions
3. **Data** — fetch/generate/load data with error handling
4. **Summary** — key metrics, data shape, freshness
5. **Visualizations** — multiple Plotly figures
6. **Table** — raw data display (first N rows)
7. **Export** — download buttons (CSV, Excel, JSON)

**Why this order matters:**
- Setup first: dependencies are clear
- Data before viz: readers understand the source
- Summary before viz: readers know what to expect
- Export last: gives users actionable next step

---

### 4. **GitHub Actions Workflow for Jupyter Notebooks**

**Pattern:**
```yaml
name: Deploy Jupyter Notebooks
"on":
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: pip install jupyter nbconvert
      - run: |
          # Convert each notebook to HTML
          for nb in dashboards/*.ipynb; do
            jupyter nbconvert --to html "$nb"
          done
      - uses: actions/upload-pages-artifact@v2
        with:
          path: dashboards
  deploy:
    needs: build
    uses: actions/deploy-pages@v2
```

**Key gotchas:**
- ⚠️ Quote `"on"` keyword (YAML reserves it as boolean)
- ⚠️ Avoid heredoc in YAML (parser chokes on metacharacters)
- ⚠️ Use `|| true` on commands that might fail (tests, conversions)
- ⚠️ Pin dependency versions (Python, pip packages)

**Best practice:**
- Test locally with `act` before pushing
- Validate YAML immediately after writing
- Keep workflow simple (complex logic → scripts in repo)

---

### 5. **Verification Suite for Multi-File Projects**

**What to check:**
1. File structure (all expected files exist)
2. JSON syntax (if using notebooks/config JSON)
3. YAML syntax (if using config/workflow files)
4. Cell structure (notebook cell counts in expected range)
5. Python syntax (all code cells parse without SyntaxError)
6. Critical imports (required packages are available)

**Pattern:**
```bash
# Check JSON
python3 -c "import json; json.load(open('file.json'))" && echo "✓" || echo "✗"

# Check YAML
python3 -c "import yaml; yaml.safe_load(open('file.yml'))" && echo "✓" || echo "✗"

# Check Python syntax
python3 -c "import ast; ast.parse(open('file.py').read())" && echo "✓" || echo "✗"
```

**ROI:** 15 mins of verification suite = 30+ mins saved in debugging post-merge

---

## Common Pitfalls

### Pitfall 1: Hard Failures on API Unavailability
❌ **Bad:** `df = socrata_client.fetch(...)  # Crashes if API down`  
✅ **Good:** `df = try_fetch() or generate_sample()`

### Pitfall 2: No Export Options
❌ **Bad:** Data stuck in notebook; user has to copy-paste  
✅ **Good:** Buttons to download CSV/Excel/JSON

### Pitfall 3: Notebook Cell Bloat
❌ **Bad:** 50 cells in one notebook; hard to navigate  
✅ **Good:** 10-12 cells max; use markdown sections to separate themes

### Pitfall 4: YAML in GitHub Actions
❌ **Bad:** Heredoc with HTML/special characters → parse fails  
✅ **Good:** Keep workflow simple; use `run: python script.py`

### Pitfall 5: No Verification Before Merge
❌ **Bad:** Broken JSON/YAML merged → CI fails 24 hrs later  
✅ **Good:** Verify locally before commit

---

## Templates

### Quick-Start Notebook Template

See: `.claude/templates/interactive-dashboard-notebook.ipynb`

Structure:
- Setup cell (imports + config)
- Control cell (ipywidgets)
- Data fetch cell (try/except pattern)
- 3-5 visualization cells (each with one chart)
- Export cell (buttons)

### Verification Script Template

See: `.claude/templates/verify-multifile.sh`

Checks: JSON, YAML, Python syntax, file existence, dependency availability

---

## Metrics & Success Criteria

**For interactive Jupyter dashboards:**
- ✅ Works offline (sample data fallback)
- ✅ Users can export data (CSV/Excel/JSON)
- ✅ All charts are interactive (Plotly, not static PNG)
- ✅ No hard errors (graceful degradation)
- ✅ Documentation covers setup + deployment
- ✅ GitHub Actions auto-deploys on push

---

## When to Apply This

**Use this pattern when:**
- Building exploratory dashboards for analysts
- Publishing data-driven documentation
- Creating educational materials with live data
- Need offline-capable data tools

**Don't use when:**
- Real-time dashboards (WebSocket, >100 updates/sec)
- High-security data (sensitive PII; use backend)
- Complex business logic (>2000 lines; use Django/FastAPI)

---

## Related Learnings

- **Plotly Reference:** Dash Mission Control app in `app/dash_app.py`
- **Data Fallbacks:** See `src/socrata_toolkit/core/client.py` (SocrataClient error handling)
- **GitHub Actions:** `.github/workflows/*.yml` in this repo
- **Sample Data Generation:** Patterns in `jupyter_book/dashboards/*.ipynb`

---

**Learning Logged By:** Claude Assistant  
**Date:** 2026-06-16  
**Confidence Level:** High (based on hands-on implementation)  
**Ready to Share:** Yes — recommend for future dashboard projects

