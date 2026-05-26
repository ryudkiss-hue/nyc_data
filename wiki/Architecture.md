# 🏗️ Architecture

How Manhattan Mission Control is organized and how the components fit together.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Manhattan Mission Control                      │
│                                                                   │
│  ┌───────────────────────────┐  ┌────────────────────────────┐  │
│  │  🌐 Browser App           │  │  🏢 Agency Dashboard       │  │
│  │  (mission_control_v2.html)│  │  (Streamlit + Python)      │  │
│  │                           │  │                            │  │
│  │  • Vanilla JS + HTML      │  │  • app/app.py (entry pt.)  │  │
│  │  • Leaflet.js (maps)      │  │  • app/views/ (pages)      │  │
│  │  • No server required     │  │  • app/analytics.py        │  │
│  │  • Hosted on GitHub Pages │  │  • app/data_loader.py      │  │
│  │  • localStorage session   │  │  • app/services/           │  │
│  └─────────────┬─────────────┘  └────────────┬───────────────┘  │
│                │                              │                   │
│                └──────────────┬───────────────┘                  │
│                               │                                   │
│                    ┌──────────▼──────────┐                       │
│                    │   Socrata REST API   │                       │
│                    │  (NYC Open Data)     │                       │
│                    │  data.cityofnewyork  │                       │
│                    │  .us/resource/*.json │                       │
│                    └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Layout

```
nyc_data/
│
├── app/                              # Streamlit agency dashboard
│   ├── app.py                        # Entry point + sidebar nav
│   ├── analytics.py                  # Workflow analytics engine
│   ├── data_loader.py                # Socrata ingestion + parquet cache
│   │
│   ├── services/
│   │   └── agency.py                 # Health checks, completeness, log tail
│   │
│   ├── ui/
│   │   ├── theme.py                  # inject_theme(), render_agency_header()
│   │   └── empty_states.py           # Onboarding UI when no data loaded
│   │
│   ├── utils/
│   │   └── i18n.py                   # Internationalization (EN/ES)
│   │
│   ├── views/
│   │   ├── home.py                   # Home / onboarding page
│   │   ├── workflows.py              # All 5 workflow view renderers
│   │   ├── publish.py                # Publish & Pack page
│   │   └── settings.py              # Settings (readiness, health, cache, logs)
│   │
│   └── static/
│       └── mission_control_v2.html   # 🌟 Standalone browser app (5,000+ lines)
│
├── src/socrata_toolkit/              # Core Python library
│   ├── core/
│   │   ├── cli.py                    # `socrata` CLI entry point
│   │   ├── readiness.py              # run_readiness_checks()
│   │   ├── ingest.py                 # Socrata API client
│   │   └── publish.py                # Email, Teams, S3 publishing
│   └── analyst/
│       └── workflows/                # Analyst pack workflow modules
│
├── config/
│   ├── datasets.yaml                 # Socrata dataset registry (source of truth)
│   ├── analyst_profile.example.yaml  # Template for analyst config
│   └── publish_profile.example.yaml  # Template for publish targets
│
├── docs/                             # 80+ documentation files
├── wiki/                             # GitHub Wiki source (markdown)
│
├── data/local_db/                    # Runtime data (gitignored)
│   ├── socrata_cache/                # .parquet files (24h TTL)
│   └── *.duckdb                      # DuckDB databases
│
├── outputs/                          # Generated outputs (gitignored)
│   ├── reports/                      # PDF, Excel, CSV exports
│   └── logs/ingest.jsonl             # Ingestion event log
│
├── tests/                            # pytest test suite
│
├── .github/workflows/
│   ├── pages.yml                     # GitHub Pages auto-deploy
│   └── (ci.yml if present)           # CI linting + tests
│
├── .env.example                      # Environment variable template
├── render.yaml                       # Render.com blueprint
├── Procfile                          # Heroku/Railway process file
├── docker-compose.yml                # Docker local dev
└── pyproject.toml                    # Python package definition
```

---

## Browser App Architecture

The HTML app (`mission_control_v2.html`) is a single-file app with no external dependencies except CDN libraries.

### State Management

All application state lives in `AppState`:

```javascript
const AppState = {
  // Core
  cart: [],           // Dataset cart (max 50)
  searchResults: [],  // Current search results
  currentDataset: null,

  // Persistence
  favorites: new Set(),     // localStorage
  workspaces: {},           // localStorage
  notifications: [],        // in-memory

  // History
  cartHistory: [],    // Undo stack
  cartFuture: [],     // Redo stack
  soqlHistory: [],    // SOQL query history
  savedQueries: [],   // Named saved queries

  // UI
  theme: 'light',          // localStorage
  fontSize: 'medium',      // localStorage
  highContrast: false,      // localStorage
  recentlyViewed: [],       // localStorage
};
```

### Key Modules

| Module | Functions | Description |
|--------|-----------|-------------|
| **Search** | `performSearch()`, `sortAndRenderResults()`, `renderCategoryPills()` | Socrata catalog search |
| **Cart** | `addToCart()`, `removeFromCart()`, `cartUndo()`, `cartRedo()` | Dataset collection |
| **SOQL** | `executeSOQL()`, `renderSoqlChart()`, `plotSoqlResultsOnMap()` | Query execution + viz |
| **Map** | `initMap()`, `haversineKm()`, `exportMapPNG()` | Leaflet map operations |
| **AI** | `explainDataset()`, `setAIPrompt()`, `colTypeIcon()`, `isPII()` | Dataset analysis |
| **Code Gen** | `genPythonCode()`, `genRCode()`, `genJSCode()`, `genGithubActionsYAML()`, `exportJupyterNotebook()`, `genReadmeMd()` | Code generation |
| **Workspace** | `saveWorkspace()`, `loadWorkspace()`, `exportWorkspace()` | Session management |
| **Export** | `exportMarkdownReport()`, `showQRCode()`, `showCitation()`, `showEmbed()`, `emailWorkspace()` | Sharing & export |
| **UI** | `applyTheme()`, `adjustFontSize()`, `toggleHighContrast()`, `toggleNotifCenter()` | Visual customization |
| **Accessibility** | `announceResults()` | ARIA announcements |

### External Libraries (CDN)

| Library | Version | Purpose |
|---------|---------|---------|
| Leaflet.js | 1.9.4 | Interactive maps |
| Leaflet.heat | latest | Heatmap overlay |
| Leaflet.markercluster | 1.5.3 | Marker clustering |
| QRCode.js | 1.0.0 | QR code generation |
| html2canvas | latest | Map PNG export |

No framework (React, Vue, etc.) — pure vanilla JS for zero build complexity.

---

## Streamlit Dashboard Architecture

### Data Flow

```
config/datasets.yaml
       │
       ▼
app/data_loader.py (DATASET_REGISTRY, WORKFLOW_DATASETS)
       │
       ├── fetch_datasets_for_keys()
       │     └── Socrata API → parquet cache → DataFrame
       │
       └── app/app.py
             ├── _load_workflow_frames(view_key, limit)
             ├── _load_all_frames(limit)
             └── _load_map_layers(limit)
                    │
                    ▼
             app/analytics.py → run_all_workflows(frames)
                    │
                    ▼
             app/views/workflows.py → render_*() functions
```

### Caching Strategy

The dashboard uses Streamlit's `@st.cache_data` decorator:

| Cache | TTL | Content |
|-------|-----|---------|
| Workflow datasets | `CACHE_TTL_SECONDS` (from data_loader) | Socrata API results |
| All datasets | Same | Full ingestion matrix |
| Map layers | Same | Geographic data |
| Workflow results | 600s | Analytics computation |
| Parquet files | 24h | Disk-based cache in `data/local_db/socrata_cache/` |

### Session State

| Key | Content |
|-----|---------|
| `workflow_data_loaded` | Boolean — data was fetched successfully |
| `completeness` | Dict of checkbox states for Settings → Completeness |

---

## Deployment Architecture

```
GitHub Repository (ryudkiss-hue/nyc_data)
│
├── Push to main
│   │
│   ├── → GitHub Actions: pages.yml
│   │       └── Deploy mission_control_v2.html → GitHub Pages
│   │               URL: https://ryudkiss-hue.github.io/nyc_data/
│   │
│   └── → GitHub Actions: ci.yml (if configured)
│           └── ruff check + pytest
│
└── render.yaml → Render.com
        └── pip install + streamlit run app/app.py
                URL: https://your-service.onrender.com
```

---

## Configuration Registry

The dataset registry (`config/datasets.yaml`) is the **single source of truth** for all Socrata dataset IDs, names, and workflow assignments.

```yaml
datasets:
  sidewalk_inspections:
    id: "nc67-uf89"
    name: "Sidewalk Inspection Results"
    workflows: [qa, spatial, quality]

  permit_applications:
    id: "......"
    name: "Permit Applications"
    workflows: [contract]
```

This drives:
- `DATASET_REGISTRY` in `data_loader.py`
- `WORKFLOW_DATASETS` mapping (which datasets load per workflow)
- Cache keys for parquet files

---

*[[Home]] · [[Getting-Started]] · [[Deployment-Guide]] · [[Changelog]]*
