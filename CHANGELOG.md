# Changelog

All notable changes to the NYC Sidewalk Data Toolkit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 84-Initiative Optimization Program

Additive upgrade across the SPA, Electron shell, and Python layer. The
Streamlit app is unchanged. Frameworks: WCAG 2.2 AAA, DAMA-DMBOK, W3C PROV
lineage, FAIR principles. See `docs/IMPROVEMENTS_PLAN.md` for the full record.

### Added

#### Data governance (Python)
- **FAIR metadata catalog** (`socrata_toolkit.fair`): `FairDataset`/`SchemaField`
  model, transparent `score_fairness()` rubric (0–100 + gap list), `FairCatalog`
  with JSON persistence and **DCAT JSON-LD** export, registry bridge from
  `config/datasets.yaml`. (11 tests)
- **PII scanner** (`socrata_toolkit.privacy.pii_scanner`): multi-signal detection
  (column-name heuristics + value regex + Luhn credit-card check + entropy/
  uniqueness), severity classification.
- **Masking utilities** (`...privacy.masking`): redact, deterministic salted
  hash token, numeric bucketing, geo truncation, partial mask, strategy
  recommendation (reversibility documented).
- **DAMA-DMBOK scorer** (`...privacy.dmbok`): all six dimensions
  (completeness, validity, uniqueness, consistency, timeliness, accuracy) with
  documented formulas and weighted overall. (privacy suite: 18 tests)

#### Analytics sidecar (Python + Electron)
- **FastAPI sidecar** (`app/sidecar_api.py`, localhost-only, lazy imports):
  health/capability probe, Bayesian Beta-Binomial yield rate (PyMC ADVI with
  Beta-bootstrap fallback), Prophet forecast, PII scan, DMBOK score, FAIRness
  score, pure-numpy anomaly detection. Graceful 503 when optional deps absent.
  Wired into Electron `main.js`. (10 tests)

#### SPA — accessibility (WCAG 2.2 AAA)
- Semantic landmarks; ARIA tablist (roving tabindex, arrow/Home/End nav);
  modal focus-trap + restoration; `prefers-color-scheme`/`prefers-contrast`
  detection; ARIA live error/status announcements; skip-to-content link;
  AAA-contrast focus rings; auto aria-labels; reduced-motion JS guard.

#### SPA — UX
- Command palette (Ctrl/Cmd+P, fuzzy search); toast notification history;
  resilient `mmcFetch` (retry + backoff + 429 Retry-After); skeleton loaders.

#### SPA — data visualization
- Pure-canvas charts (offline, Okabe-Ito color-blind-safe palette, HiDPI,
  a11y table fallbacks): bar, histogram, box-plot stats, sparkline, correlation
  heatmap.

#### SPA — Governance tab
- Per-dataset DAMA-DMBOK scorecard, FAIRness scorecard (F/A/I/R + gaps), PII
  inspector with severity chips; client-side scoring that mirrors the Python
  modules and uses the sidecar when running in Electron; JSON report export.

#### SPA — performance
- sessionStorage LRU cache with TTL; virtualized table rendering; inline Web
  Worker for large sorts; lazy panel init; runtime Web-Vitals-style timing.
  See `docs/PERFORMANCE_BUDGET.md`.

#### Desktop (Electron)
- Offline CDN vendoring (Tailwind, FontAwesome, Leaflet, MarkerCluster,
  Mermaid, svg-pan-zoom, html2canvas) with build-time URL rewriting; branded
  NYC-skyline app icons (ico/icns/png).

## [3.0.0] - 2026-05-11

### Added

#### LangChain AI Integration
- **LLM Chatbot** - Multi-turn conversational AI with dataset context awareness
  - Support for Ollama, OpenAI, and Hugging Face LLM backends
  - Conversation history management with configurable window size
  - Dataset-aware responses using metadata
  - Specialized Data Quality Assistant for issue assessment
  - Specialized Analytics Advisor for metric suggestions and pattern identification
  
- **SQL Query Engine** - Wolfram-like natural language to SQL translation
  - Automatic database schema introspection
  - Query safety validation (blocks DELETE, DROP, ALTER operations)
  - Automatic result interpretation via LLM
  - Interactive query sessions with context-aware follow-ups
  - Query execution history and audit trail
  - Query optimizer with optimization suggestions
  
- **FastAPI Routes** - Complete REST API for LLM features
  - Chat endpoints: `/chat`, `/chat/history`, `/chat/clear`, `/chat/suggest-analyses`
  - Query endpoints: `/query`, `/query/session/{id}`, `/query/schema`
  - Quality assessment: `/quality/assess`
  - Analytics: `/analytics/suggest-metrics`
  - Health checks: `/health`

#### React/TypeScript Frontend
- **Modern Web UI** built with Vite + React 18 + TypeScript
- **ChatInterface Component** - Multi-turn conversational messaging
  - Real-time message streaming
  - Auto-scroll to latest messages
  - Clear conversation history
  - Provider and model selection
  - Loading and error states
  
- **QueryBuilder Component** - SQL query execution interface
  - Natural language query input
  - Generated SQL display with copy functionality
  - Results visualization with statistics
  - Results table with pagination
  - Query interpretation display
  
- **App Layout & Navigation**
  - Collapsible sidebar with settings
  - Multi-tab interface (Chat/Query/Quality)
  - Dark mode toggle with persistent preference
  - System status indicator
  - Professional NYC blue theme
  
- **State Management** - Zustand store
  - Chat message history
  - UI state (tabs, dark mode, sidebar)
  - Settings (provider, model, theme)
  - Error and loading states
  
- **Styling & Responsive Design**
  - TailwindCSS with NYC blue color palette
  - Dark mode support
  - Mobile-responsive layout
  - Professional component design

#### Documentation
- **LANGCHAIN_INTEGRATION_GUIDE.md** - Complete LLM integration guide
  - Setup for all LLM providers (Ollama, OpenAI, Hugging Face)
  - Quick start examples with code
  - Advanced usage patterns
  - CLI integration guide
  - FastAPI integration examples
  - Streamlit web UI integration
  - Performance tuning and optimization
  - Best practices and troubleshooting

- **Documentation Index** - Central hub for all 49+ guides
  - Role-based navigation (analyst, admin, developer, DevOps)
  - Task-based navigation (install, query, integrate, monitor)
  - Quick reference links
  - Support and feedback channels

#### Configuration
- **.env.example** - Comprehensive environment configuration template
  - Database configuration (PostgreSQL, MongoDB)
  - API configuration
  - Frontend configuration
  - LLM configuration for all providers
  - Socrata API configuration
  - Security and authentication
  - Logging and debugging
  - Production configuration
  - Email alerts
  - Cloud provider setup (AWS, Azure, GCP)
  - Docker configuration
  - Feature flags

#### Developer Experience
- **CONTRIBUTING.md** - Complete contribution guidelines
  - Code of conduct
  - Development setup instructions
  - Branching strategy and commit message conventions
  - Coding standards (Python, TypeScript, SQL)
  - Testing requirements and examples
  - Documentation standards
  - Pull request process
  
- **Frontend documentation**
  - frontend/README.md - Architecture and features
  - frontend/SETUP.md - Detailed setup instructions with troubleshooting
  - API client types and methods
  - Component documentation
  - Styling guide

### Changed

#### Dependencies
- Updated `pyproject.toml` with LangChain ecosystem packages
  - `langchain`, `langchain-community`
  - `ollama`, `openai`, `huggingface-hub`
  - `pydantic` for data validation
  - `sqlalchemy` for database abstraction

### Technical Improvements

- **Type Safety** - Full TypeScript in frontend, type hints in Python backend
- **Error Handling** - Comprehensive error handling with meaningful messages
- **API Design** - RESTful design with Pydantic models and async support
- **Code Organization** - Clean separation of concerns across backend and frontend
- **Documentation** - 49+ guides covering all aspects of the toolkit

## [2.0.0] - 2026-04-15

### Added
- Executable package with CLI and Web UI
- Docker containerization for deployment
- Comprehensive deployment guides
- Makefile with 40+ build commands
- Complete CLI command reference
- QUICKSTART and EXECUTABLE_PACKAGE documentation

### Changed
- Reorganized project structure for modularity
- Enhanced API architecture
- Improved deployment configurations

## [1.0.0] - 2026-03-01

### Added
- Initial NYC Sidewalk Data Toolkit release
- Core CLI functionality
- Data pipeline support
- Material standards and compliance checking
- Sidewalk inspection management
- Entity resolution capabilities
- Spatial analysis features
- Master data management
- Data quality framework
- Basic API endpoints
- Documentation foundation

---

## [Unreleased]

### Added

- **Analyst Autopilot** (`socrata_toolkit/analyst/`) — YAML-driven weekly analyst pack: construction list prioritization, permit conflict summary, contract report, program KPI JSON, inquiry drafts, and `manifest.json` under `outputs/analyst_pack/`.
- **Analyst pack artifacts** — `construction_list_diff.md`, `conflicts_review.xlsx`, `executive_summary.html`/`.md`, enhanced manifest (sources, row counts, version, partial failures), inquiry template library (`config/inquiry_templates/`), golden Excel headers (`config/templates/`), optional `config/budget_codes.yaml`.
- **Offline mode** — profile flag `offline: true` skips Socrata sources.
- **Dash analyst GUI** — streamlined sidebar (Home, Construction, Contracts, Metrics, Inquiries, Settings); accessible KPI indicators; Run Analyst Pack on Home.
- **Example analyst profile** — `config/analyst_profile.example.yaml` with Excel, Postgres, and Socrata source templates.
- **Pipeline incremental sync** — `socrata_toolkit/pipeline/sync.py` and `socrata sync` CLI command for incremental Socrata → DuckDB loads with optional VACUUM/ANALYZE and Parquet export.
- **End-user documentation** — `docs/USER_MANUAL.md`, `docs/GETTING_STARTED.md`, `docs/FAQ.md`, `docs/TROUBLESHOOTING.md`, `docs/COMMAND_REFERENCE.md`.

### Changed

- **Dependencies** — LangChain, OpenAI, Ollama, and Hugging Face moved to optional `[llm]` extra (not installed by default).
- **Primary GUI** — Dash (`dash_app/app.py`) is the analyst-facing app; devtools/quantum/geospatial pages register only when `NYC_DOT_DEBUG=1`.
- **CLI surfaces documented** — Installed `socrata` entry point (`socrata_toolkit.cli`) exposes search/fetch/analyze/sync/status/map-toolkit; extended commands remain on `python -m socrata_toolkit.core.cli` until entry-point merge is complete.
- **Modular package layout** — Quality and spatial packages restored; tests aligned with modular APIs (see git history `8fd6508`, `f405358`, `b4412d3`).

### Documentation

- README Documentation section links to new analyst-facing guides.
- User manual documents Dash as the primary analyst GUI; NiceGUI/Streamlit launcher paths deprecated for new workflows.

### In Development

- `socrata analyst-pack` CLI subcommand wiring to `run_analyst_pack()`
- Unified `socrata` entry point delegating to `core.cli` for pipeline/conflict/schema commands
- GraphQL API endpoints
- ML-based anomaly detection
- ArcGIS Pro integration

### Planned

- Predictive maintenance models
- Mobile app for field inspections
- Kubernetes multi-cluster support

---

## [0.4.0] - TBD

Planned release tag bundling Analyst Autopilot, pipeline sync, and documentation above once CLI merge and integration tests are complete.

---

## Version Naming

Versions follow Semantic Versioning:
- **MAJOR** (3.0.0) - Breaking changes
- **MINOR** (3.1.0) - Backward-compatible new features
- **PATCH** (3.0.1) - Bug fixes and minor improvements

---

## How to Report Issues

Found a bug or have a feature request?

1. Check existing [GitHub Issues](https://github.com/ryudkiss-hue/nyc_data/issues)
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Screenshots or logs if relevant

---

## How to Get Involved

Interested in contributing?

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Check [GitHub Issues](https://github.com/ryudkiss-hue/nyc_data/issues) for open tasks
3. Fork the repository and create a feature branch
4. Submit a pull request with your improvements

---

## Acknowledgments

This toolkit was built to support NYC's sidewalk management and maintenance operations. Thanks to all contributors and users who help improve it.

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Release History

| Version | Date | Notes |
|---------|------|-------|
| 3.0.0 | 2026-05-11 | LangChain AI integration, React frontend, comprehensive documentation |
| 2.0.0 | 2026-04-15 | Executable package, Docker, deployment guides |
| 1.0.0 | 2026-03-01 | Initial release |

For detailed migration guides, see [docs/releases.md](docs/releases.md)
