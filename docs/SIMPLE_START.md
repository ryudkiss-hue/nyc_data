# Simple start (5 minutes)

NYC DOT Sidewalk Toolkit — one path from install to published pack.

## 1. Install

**Windows (recommended for analyst PCs):** run the installer built from this repo.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
# Output: installer\output\NYC-DOT-Sidewalk-Toolkit-Setup.exe
```

Double-click **NYC-DOT-Sidewalk-Toolkit-Setup.exe**, then use Start Menu → **Setup Wizard**.

**Developers / Mac / Linux:** use Python in the repo folder.

```bash
pip install -e ".[xlsx]"
python -m socrata_toolkit.install_wizard
```

The wizard creates `.env` and copies `config/analyst_profile.example.yaml` → `config/analyst_profile.yaml`.

## 2. Run the weekly pack

```bash
socrata analyst run --profile config/analyst_profile.yaml
```

Or: open the dashboard (step 3) and click **Run Analyst Pack** on Home.

Outputs land in `outputs/analyst_pack/YYYY-MM-DD/` (Excel, Markdown, HTML, JSON).

## 3. Open Mission Control Dashboard

```bash
pip install -e ".[mission,postgres,xlsx]"
python app/dash_app.py     # PRIMARY: Dash Mission Control
# or: python main.py       # Launcher shim (auto-selects primary)
```

No Socrata token? Demo mode loads automatically (or set `MISSION_DEMO=1`).

Browser: **http://localhost:8011** (Dash Mission Control — PRIMARY)

**Secondary option (Streamlit):** `streamlit run app/app.py` → http://localhost:8501

**Alternative — Render one-click deploy:** push the repo to GitHub and connect it at [render.com](https://render.com) → New Blueprint. No local setup required; `render.yaml` handles everything. Set `SOCRATA_APP_TOKEN` in the Render dashboard for live data.

| Tab | What to do |
|-----|------------|
| **Home** | Load datasets, see audit trail |
| **Agency Workflows** | QA / Spatial / Contract / Productivity views |
| **Data Quality** | Health scores, SLA freshness, CSV export |
| **AI Copilot** | Chat with your data (set `GEMINI_API_KEY` or `OPENAI_API_KEY`) |
| **Settings & Quality** | Readiness score, system health |

## 4. Nightly pack (optional)

Schedule the weekly analyst pack on Windows Task Scheduler:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\nightly_analyst_sync.ps1
```

Then review in Mission Control: `python main.py`.

## 5. Publish (optional)

```bash
socrata analyst publish --profile config/publish_profile.yaml
```

Copy `config/publish_profile.example.yaml` first and set your share paths.

## Need more?

- Full manual: [USER_MANUAL.md](USER_MANUAL.md)
- Windows installer details: [WINDOWS_INSTALLER.md](WINDOWS_INSTALLER.md)
- Commands: [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)
- Problems: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Optional Python extras (only if you need them):

```bash
pip install -e ".[postgres]"   # PostgreSQL sources
pip install -e ".[llm]"        # AI chat / NLQ (heavy)
pip install -e ".[nlp]"        # Text enrichment (spacy)
pip install -e ".[geo,viz]"    # Maps and charts
```

Developer-only Dash pages (quantum, devtools, analytics lab): set `NYC_DOT_DEBUG=1` before starting the dashboard.
