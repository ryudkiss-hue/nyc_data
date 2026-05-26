# 📖 Feature Reference

Complete guide to every feature in Manhattan Mission Control V2.

---

## 🔍 Search

### Basic Search
Type any keyword in the main search bar and press Enter or click the 🔍 button.

**Examples:**
- `sidewalk` — all datasets related to sidewalk inspections
- `311 complaints` — citizen service requests
- `bicycle` — bike lane and cycling data
- `flood zone` — emergency planning data

### Advanced Filters

After searching, use the filter panel to narrow results:

| Filter | Options |
|--------|---------|
| **Category** | Transportation, Housing, Health, Environment, Public Safety, Finance… |
| **Data Type** | Table, Map, Calendar, Chart, File |
| **Freshness** | Updated this week / month / year |
| **Tag** | Click any tag pill to filter by topic |

### Sort Options

Click **Sort** to change result ordering:
- **Relevance** (default)
- **Name A→Z**
- **Most viewed**
- **Recently updated**
- **Row count**

### Sample Searches

Click the quick-access chips below the search bar for common topics:
- 🚦 Traffic
- 🏗️ Sidewalk
- 🏠 Housing
- 🆘 311 Calls
- 🌳 Parks
- 🅿️ Parking

---

## 🛒 Dataset Cart

The cart lets you collect, compare, and export multiple datasets.

### Adding Datasets

- **Single add:** Click the 🛒 cart icon on any search result card
- **Bulk add:** Check multiple results and click **Add Selected to Cart**

### Cart Capacity
Up to **50 datasets** can be in the cart at once.

### Cart Actions

| Button | Action |
|--------|--------|
| 🗑️ Remove | Remove one dataset from the cart |
| 🗑️ Clear All | Empty the cart |
| ↩️ Undo | Undo last cart change (Ctrl+Z) |
| ↪️ Redo | Redo undone change (Ctrl+Y) |
| 📊 Compare | Side-by-side dataset comparison |
| 📤 Export All | Download all cart datasets |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo cart change |
| `Ctrl+Y` | Redo cart change |
| `Ctrl+E` | Export cart |
| `Ctrl+K` | Focus search bar |

---

## 📊 SOQL Query Studio

The Query Studio lets you write live SQL-like queries against any dataset.

### Opening SOQL Studio

Click the **SOQL Studio** tab or the `{SQL}` button on any dataset card.

### Writing Queries

```sql
-- Basic select with filter
SELECT inspection_id, street_name, borough, status
WHERE borough = 'MANHATTAN'
LIMIT 100

-- Count by category
SELECT status, COUNT(*) AS total
GROUP BY status
ORDER BY total DESC

-- Date filter
SELECT *
WHERE created_date >= '2024-01-01T00:00:00.000'
  AND created_date < '2024-12-31T23:59:59.000'
```

### Templates

Click **📋 Templates** for pre-written queries:
- Top 10 by count
- Group by category
- Date range filter
- Geographic filter
- Null value check
- Trend analysis

### Query History

Click **🕐 History** to see your recent queries. Click any to re-run it.

### Visualizing Results

After running a query:
- **📊 Chart** — Auto-renders a bar or line chart
- **🗺️ Map** — Plots results on an interactive map (if data has coordinates)
- **📋 Table** — Standard tabular view (default)

### Exporting Query Results

- **⬇ CSV** — Download as comma-separated values
- **⬇ JSON** — Download as JSON array
- **📋 Copy** — Copy to clipboard

---

## 🗺️ Map Viewer

### Accessing the Map

Click the **🗺️ Map** button on any dataset card that contains geographic data (look for the 📍 icon indicating geospatial data).

### Map Controls

| Control | Description |
|---------|-------------|
| **Layer picker** | Switch between Street, Satellite, and Dark tile layers |
| **Heatmap toggle** | Show/hide density heatmap overlay |
| **Cluster toggle** | Group nearby markers (helpful for dense datasets) |
| **🎯 Recenter** | Zoom back to New York City |
| **📏 Measure** | Haversine distance tool — click two points to measure |
| **📸 Export PNG** | Save the current map view as a PNG image |

### Drawing Tools

- **Point** — Drop a marker
- **Circle** — Draw a circle with configurable radius
- **Rectangle** — Draw a bounding box
- **Clear** — Remove all drawings

---

## 🤖 AI Assistant

> **Note:** The AI assistant provides intelligent suggestions based on dataset metadata. It uses pattern matching and built-in knowledge — no external API key required.

### What it can do

| Feature | How to use |
|---------|-----------|
| **Explain a dataset** | Click **🤖 Explain** on any dataset card |
| **Suggest related data** | Click **🔗 Related** to see similar datasets |
| **Generate a query** | Describe what you want in the prompt box |
| **Analyze column types** | Auto-detects dates, numbers, IDs, PII |
| **Summarize schema** | Shows column types, null rates, key fields |

### Prompt Templates

Click **📝 Templates** in the AI panel for common prompts:
- *"Explain this dataset in plain English"*
- *"What are the most important columns?"*
- *"Suggest a SOQL query to find [topic]"*
- *"What other datasets complement this one?"*
- *"Flag any potential privacy or PII concerns"*

---

## 💻 Code Generation

Generate ready-to-run code for any dataset.

### Accessing Code Generator

Click **`</> Code`** on any dataset card or in the cart detail view.

### Available Languages

#### Python (pandas + sodapy)
```python
from sodapy import Socrata
import pandas as pd

client = Socrata("data.cityofnewyork.us",
                 "YOUR_APP_TOKEN")

results = client.get("DATASET_ID", limit=2000)
df = pd.DataFrame.from_records(results)
print(df.head())
```

#### R (httr + jsonlite)
```r
library(httr)
library(jsonlite)

url <- "https://data.cityofnewyork.us/resource/DATASET_ID.json"
response <- GET(url, query = list("$limit" = 1000))
df <- fromJSON(content(response, "text"))
head(df)
```

#### JavaScript (fetch)
```javascript
const response = await fetch(
  'https://data.cityofnewyork.us/resource/DATASET_ID.json?$limit=100'
);
const data = await response.json();
console.table(data);
```

#### GitHub Actions (automated pipeline)
```yaml
name: Daily Data Refresh
on:
  schedule:
    - cron: '0 6 * * *'
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch dataset
        run: |
          curl "https://data.cityofnewyork.us/resource/DATASET_ID.json" \
            > data.json
```

#### Jupyter Notebook
Downloads a complete `.ipynb` file with:
- Dataset metadata cell
- Data loading cell
- Basic EDA (describe, head, dtypes)
- Placeholder visualization cell
- Export cell

---

## 💾 Workspaces

Save and restore your entire session — search query, filters, cart, SOQL history.

### Saving a Workspace

1. Click **💾 Save Workspace** in the sidebar
2. Enter a name (e.g., "Sidewalk Defects Q1 2024")
3. Click **Save**

### Restoring a Workspace

Click **📂 Load Workspace** → select from the list.

### Sharing Workspaces

| Share method | How |
|-------------|-----|
| **QR Code** | Click **📱 QR Code** — scan with phone |
| **Email link** | Click **✉️ Email** — opens mail client with encoded link |
| **Export JSON** | Click **⬇ Export** — downloads workspace as JSON |
| **Import JSON** | Click **⬆ Import** — loads a workspace JSON file |

---

## 📤 Export & Sharing

### From a Dataset Card

| Export | Format |
|--------|--------|
| **Download CSV** | Comma-separated values |
| **Download JSON** | Raw API response |
| **Download GeoJSON** | Geographic features (for map datasets) |
| **Citation** | APA, Chicago, or MLA format |
| **Embed Code** | `<iframe>` HTML for embedding in websites |

### From the Cart

| Export | Content |
|--------|---------|
| **Markdown Report** | Formatted analysis summary with table of contents |
| **Jupyter Notebook** | Multi-dataset analysis notebook |
| **Export All CSV** | ZIP of all cart datasets as CSV |
| **README.md** | Auto-generated project README |

---

## ♿ Accessibility

### Keyboard Navigation

| Key | Action |
|----|--------|
| `Tab` | Move to next focusable element |
| `Shift+Tab` | Move to previous element |
| `Enter` / `Space` | Activate button or checkbox |
| `Escape` | Close modal or dropdown |
| `Arrow keys` | Navigate within menus |
| `?` | Open Help Center |
| `Ctrl+K` | Focus search bar |

### Screen Reader Support

- All interactive elements have `aria-label` attributes
- Search results are announced via ARIA live region
- Modal dialogs use `role="dialog"` with proper focus management
- Status updates appear in `#aria-live` (polite announcements)

### Visual Settings

| Setting | Access |
|---------|--------|
| **Dark mode** | 🌙 button in header |
| **High contrast** | Accessibility menu → High Contrast |
| **Font size** | A- / A+ buttons in header |
| **Reduced motion** | Automatically respects OS setting |

---

## 🔔 Notification Center

Click the **🔔 bell** icon to open the notification center.

- Shows recent system events, search completions, export confirmations
- Click **✓ Mark all read** to clear the badge
- Individual notifications can be **dismissed**
- Notification **history** is preserved in your session

---

## ⭐ Favorites

Click the **⭐ star** on any dataset card to add it to Favorites.

Access your favorites:
- Click **⭐ Favorites** in the sidebar
- Or filter search results by "Favorites" in the filter panel

Favorites persist in **localStorage** — they survive page refreshes.

---

## 🎨 Customization

| Setting | Location |
|---------|----------|
| **Light/Dark theme** | 🌙 toggle in header |
| **High contrast** | Accessibility menu |
| **Font size** | A- / A+ buttons |
| **Density** (Compact/Comfortable/Spacious) | Settings panel |
| **Default category** | Settings panel |
| **Row limit** | Settings panel |

All settings are saved to **localStorage** and restored on next visit.

---

*[[Home]] · [[Getting-Started]] · [[SOQL-Guide]] · [[Code-Generation]] · [[Deployment-Guide]]*
