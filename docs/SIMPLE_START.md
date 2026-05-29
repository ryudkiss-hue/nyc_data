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

## 3. Open the dashboard

```bash
pip install -e ".[mission]"
python main.py
```

No Socrata token? Demo mode loads automatically (or set `MISSION_DEMO=1`).

Browser: **http://localhost:8501** (Streamlit Mission Control)

Legacy Analyst Pack UI (Dash): `python legacy_archive/dash_app/app.py` → http://127.0.0.1:8050

| Page | What to do |
|------|------------|
| **Home** | Run pack, see latest files |
| **Review** | Approve conflicts and sign-offs |
| **Publish** | Send pack to share folder, email, Teams, or BI |

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
