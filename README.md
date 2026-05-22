# NYC DOT Sidewalk Toolkit

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data)

Python toolkit for NYC DOT Sidewalk Inspection & Management: collect data, run the weekly **Analyst Pack**, review in the dashboard, and publish outputs.

**Cloud deploy:** [docs/DEPLOY_CLOUD.md](docs/DEPLOY_CLOUD.md) · **macOS/Linux build:** `scripts/build_unix.sh`

## Install (pick one)

| Who | Path | Next step |
|-----|------|-----------|
| **Windows analyst PC** | `installer\output\NYC-DOT-Sidewalk-Toolkit-Setup.exe` | Start Menu → Setup Wizard |
| **Developer / cross-platform** | `pip install -e ".[xlsx]"` then `python -m socrata_toolkit.install_wizard` | Edit `config/analyst_profile.yaml` |

Build the Windows installer: `powershell -File scripts\build_installer.ps1` — see [docs/WINDOWS_INSTALLER.md](docs/WINDOWS_INSTALLER.md).

## Daily workflow

1. **Setup** — wizard + `config/analyst_profile.yaml`
2. **Run** — `socrata analyst run --profile config/analyst_profile.yaml`
3. **Review & publish** — `python main.py` or `streamlit run app/app.py` (legacy Dash: `legacy_archive/dash_app/app.py`)

Step-by-step (no jargon): **[docs/SIMPLE_START.md](docs/SIMPLE_START.md)**

Developers: `powershell -File scripts\setup_precommit.ps1` installs ruff hooks (matches CI).

**Agency operations:** [docs/AGENCY_RUNBOOK.md](docs/AGENCY_RUNBOOK.md) · target readiness **≥ 95** via `socrata readiness`.

## Documentation

| Doc | Use when |
|-----|----------|
| [docs/SIMPLE_START.md](docs/SIMPLE_START.md) | First day on the job |
| [docs/USER_MANUAL.md](docs/USER_MANUAL.md) | Full reference |
| [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md) | CLI cheat sheet |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | Share/email/Teams/BI |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Errors and logs |
| [docs/index.md](docs/index.md) | All guides |

Config templates: `config/analyst_profile.example.yaml`, `config/publish_profile.example.yaml`

## Optional Python extras

Core install is enough for wizard, analyst pack, and Dash. Add only what you need:

```bash
pip install -e ".[postgres]"   # Postgres sources
pip install -e ".[llm]"        # LLM features (large download)
pip install -e ".[nlp]"        # spaCy text tools
pip install -e ".[geo,viz,reports,ui]"  # maps, charts, PDF, Streamlit
pip install -e ".[exe]"        # PyInstaller / Windows .exe build
```

## Tests

```bash
python -m pytest tests/ -q
```

## License

MIT
