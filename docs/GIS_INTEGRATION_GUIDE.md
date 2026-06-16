# GIS Dashboard Integration Guide

**For:** Developers integrating Phase 1 GIS Pilot into main app  
**Status:** Ready for integration  
**Prerequisites:** Dash, Plotly, Pandas, Redis

---

## Quick Start

### 1. Add GIS Layout to Main App

In `app/dash_app.py`, import the GIS layout:

```python
from app.dash_layouts_gis import layout_gis
from app.callbacks.gis import register_gis_spatial_callbacks
```

### 2. Register GIS Route

In the callback registration section of `app/dash_app.py`:

```python
# Register all callbacks
register_gis_spatial_callbacks(app, data_manager)  # data_manager is your DM instance
```

### 3. Add URL Route

In your app's URL routes (assuming you use `pages` or similar routing):

```python
# Option A: Dash Pages
# Add file: pages/gis.py
from dash import register_page
from app.dash_layouts_gis import layout_gis

register_page(__name__, path="/geo", layout=layout_gis())

# Option B: Manual routing in dash_app.py
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/geo':
        return layout_gis()
    # ... other routes ...
```

### 4. Ensure Redis is Running

```bash
# Start Redis locally
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest

# Or set Redis URL in environment
export REDIS_URL="redis://localhost:6379/0"
```

### 5. Test the Integration

```bash
python app/dash_app.py
# Navigate to http://localhost:8050/geo
```

---

## File Dependencies

### Required Files

```
app/
├── services/
│   ├── gis_service.py          ← GIS service layer (MUST exist)
│   └── cache_service.py        ← Already exists
├── callbacks/
│   └── gis.py                  ← Callback handlers (MUST exist)
└── dash_layouts_gis.py         ← Layout definition (MUST exist)

tests/
└── test_gis_callbacks.py       ← Unit tests (optional, but recommended)
```

### Optional Files (for documentation)

```
docs/
├── GIS_PILOT_PERFORMANCE_BASELINE.md
├── PHASE1_GIS_PILOT_IMPLEMENTATION_SUMMARY.md
└── GIS_INTEGRATION_GUIDE.md (this file)
```

---

## Data Flow & Integration Points

### Input: Data Store Population

**Problem:** Where does `gis-data-store` and `gis-permits-store` get populated?

**Solution:** You need to add callbacks to load data when the page loads.

```python
# In app/callbacks/gis.py or a new file

@app.callback(
    Output("gis-data-store", "data"),
    Input("gis-data-loader", "children"),  # Triggered on page load
)
def load_inspection_data(_):
    """Load inspection data from DuckDB and populate store."""
    try:
        # Load data from your data manager
        df = data_manager.fetch_dataset("inspection")  # Adjust method name
        
        # Convert to list-of-dicts for JSON serialization
        data = df.to_dict('records')
        
        return data
    except Exception as e:
        logger.error(f"Failed to load inspection data: {e}")
        return {}

@app.callback(
    Output("gis-permits-store", "data"),
    Input("gis-data-loader", "children"),
)
def load_permit_data(_):
    """Load permit data from DuckDB."""
    try:
        df = data_manager.fetch_dataset("street_permits")
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Failed to load permit data: {e}")
        return {}
```

### Output: Visualization Components

The following `dcc.Graph` components are rendered:
- `viz-condition-map` → Plotly scatter mapbox
- `viz-hotspot-kde` → KDE density heatmap
- `viz-conflict-map` → Conflict overlay map
- `viz-borough-bar` → Borough aggregation bar chart
- `viz-dbscan-clusters` → Cluster visualization

Each is updated by its corresponding callback when filters change.

---

## Configuration Options

### Filter Options

Edit `app/dash_layouts_gis.py` to customize available filters:

```python
# Borough options
dmc.MultiSelect(
    id="gis-borough-filter",
    data=[
        {"value": "MANHATTAN", "label": "Manhattan"},
        {"value": "BROOKLYN", "label": "Brooklyn"},
        # Add more as needed
    ]
)

# Severity thresholds (in callbacks/gis.py)
thresholds = {
    "CRITICAL": (0, 30),
    "HIGH": (31, 60),
    "MEDIUM": (61, 80),
    "LOW": (81, 100),
}
```

### Performance Tuning

In `app/services/cache_service.py`:

```python
# Adjust cache TTL (default: 3600s = 1 hour)
cache.set("gis-filters:...", filters, ttl_seconds=7200)  # 2 hours

# Adjust Redis compression
self.zstd_compressor = zstd.ZstdCompressor(level=10)  # 1-22, higher=more compression
```

### Map Style

In `app/services/gis_service.py`:

```python
# Change Plotly mapbox style
fig.update_layout(
    mapbox_style="carto-positron",  # Options: open-street-map, carto-positron, carto-positron-nolabels, stamen-terrain, etc.
)
```

---

## Common Customizations

### Add a New Visualization

1. **Add method to GISService:**

```python
# In app/services/gis_service.py
@staticmethod
def create_accessibility_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create heatmap of pedestrian ramp accessibility."""
    # Your implementation here
    return fig
```

2. **Create callback:**

```python
# In app/callbacks/gis.py
@callback(
    Output("viz-accessibility-heatmap", "figure"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
)
def update_accessibility_heatmap(filters, data_store):
    """Update accessibility heatmap."""
    try:
        df = pd.DataFrame(data_store)
        # Apply filters...
        return gis_service.create_accessibility_heatmap(df)
    except Exception as e:
        logger.error(f"Error: {e}")
        return go.Figure().add_annotation(text=str(e))
```

3. **Add UI component:**

```python
# In app/dash_layouts_gis.py
dmc.TabsPanel(
    value="accessibility",
    children=[
        dmc.Space(h="md"),
        dmc.Paper(
            p="lg",
            children=[
                dcc.Graph(id="viz-accessibility-heatmap")
            ]
        )
    ]
)

# Add tab to TabsList
dmc.TabsTab("♿ Accessibility", value="accessibility")
```

4. **Write test:**

```python
# In tests/test_gis_callbacks.py
def test_create_accessibility_heatmap(sample_data):
    fig = gis_service.create_accessibility_heatmap(sample_data)
    assert isinstance(fig, go.Figure)
```

### Change Default Filter Values

```python
# In app/dash_layouts_gis.py
dmc.MultiSelect(
    id="gis-borough-filter",
    value=["MANHATTAN", "BROOKLYN"],  # Default selected
    ...
)
```

### Add New Date Filter

```python
# In app/dash_layouts_gis.py
dmc.DatePickerInput(
    id="gis-start-date",
    label="Start Date",
    placeholder="Select start date",
    type="default",
)

# In app/callbacks/gis.py
@callback(
    Output("gis-session-filters", "data"),
    Input("gis-start-date", "value"),
    ...
)
def sync_gis_filters(start_date, ...):
    filters = {
        ...
        "start_date": start_date,
    }
```

---

## Testing the Integration

### Unit Tests

```bash
# Run GIS-specific tests
pytest tests/test_gis_callbacks.py -v

# Expected output:
# ======================= 31 passed in 14.70s =======================
```

### Manual Testing

1. **Start the app:**
   ```bash
   python app/dash_app.py
   ```

2. **Navigate to http://localhost:8050/geo**

3. **Test filter interactions:**
   - Change borough filter → Map should update
   - Change severity filter → Map should update
   - Change date range → Map should update

4. **Test visualizations:**
   - Click each tab → Chart should render
   - Hover over points → Tooltip appears
   - Zoom/pan map → Interaction works

5. **Test export:**
   - Click "Export CSV" button
   - File should download

6. **Monitor logs:**
   ```bash
   # Watch for errors
   tail -f app.log
   ```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app.services.gis_service'"

**Solution:** Ensure file exists at `app/services/gis_service.py`

```bash
ls -la app/services/gis_service.py
```

### Issue: "Redis connection refused"

**Solution:** Start Redis server

```bash
# Check if Redis is running
redis-cli ping
# Expected output: PONG

# If not running, start it
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

### Issue: "TypeError: register_gis_spatial_callbacks() missing 1 required positional argument"

**Solution:** Pass data_manager instance to callback registration

```python
# In app/dash_app.py
from app.data_manager import DataManager

dm = DataManager()  # Initialize your data manager
register_gis_spatial_callbacks(app, dm)
```

### Issue: "Empty maps / no data displayed"

**Solutions:**
1. Check that `gis-data-store` is populated (browser dev tools → Application → Stores)
2. Check browser console for JavaScript errors
3. Check server logs for Python errors
4. Ensure data has "latitude" and "longitude" columns

### Issue: "Callback not updating when filter changes"

**Solutions:**
1. Check that filter ID matches input in callback (e.g., "gis-borough-filter")
2. Check that dcc.Store IDs match between layout and callback
3. Check browser dev tools → Network tab for failed requests
4. Check console logs for callback execution

---

## Production Deployment

### Environment Variables

```bash
# .env file
REDIS_URL=redis://localhost:6379/0
DASH_PORT=8050
DASH_HOST=0.0.0.0
PYTHONUNBUFFERED=1
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app code
COPY app/ app/
COPY tests/ tests/

# Start app
CMD ["python", "app/dash_app.py"]
```

```bash
# Build and run
docker build -t gis-dashboard .
docker run -p 8050:8050 -e REDIS_URL=redis://redis:6379/0 gis-dashboard
```

### Performance Monitoring

```python
# Add monitoring callback
import time

@app.callback(
    Output("debug-log", "children"),
    Input("gis-session-filters", "data"),
)
def log_callback_timing(filters):
    """Log callback execution time."""
    start = time.time()
    # ... do work ...
    elapsed = time.time() - start
    logger.info(f"Callback took {elapsed:.3f}s")
```

---

## Support & Questions

### Getting Help

1. Check `docs/GIS_PILOT_PERFORMANCE_BASELINE.md` for architecture overview
2. Check `docs/PHASE1_GIS_PILOT_IMPLEMENTATION_SUMMARY.md` for implementation details
3. Review `tests/test_gis_callbacks.py` for usage examples
4. Check inline code comments and docstrings

### Reporting Issues

When reporting integration issues, include:
1. Error message (full stack trace)
2. Which callback/component is failing
3. Steps to reproduce
4. Python version, Dash version, Plotly version
5. Server logs and browser console output

---

## Next Steps (Phase 2)

Once Phase 1 is stable, Phase 2 will add:

1. **Integration Tests** (Selenium)
   - User workflow testing
   - Cross-browser compatibility
   - A/B test harness

2. **Load Testing** (Locust)
   - Concurrent user simulation
   - Performance bottleneck identification
   - Optimization recommendations

3. **Advanced Features**
   - Folium integration (GeoJSON)
   - 3D terrain visualization
   - Time-lapse animation
   - Real-time updates (WebSocket)

---

## Checklist for Successful Integration

- [ ] All files copied to correct locations
- [ ] Redis is running and accessible
- [ ] Callback registration added to main app
- [ ] URL route registered (/geo)
- [ ] Data loading callbacks implemented
- [ ] Unit tests passing (31/31)
- [ ] Manual testing completed
- [ ] No console errors or warnings
- [ ] Export functionality works
- [ ] Performance acceptable (<500ms latency)
- [ ] Documentation updated with any customizations
- [ ] Ready for staging deployment

---

**Ready to integrate?** Follow steps 1-5 above and you should be live!

**Questions?** Refer to the troubleshooting section or check the docs.

**Found a bug?** File an issue with the checklist items above filled in.

---

**Last Updated:** June 10, 2026  
**Status:** READY FOR INTEGRATION
