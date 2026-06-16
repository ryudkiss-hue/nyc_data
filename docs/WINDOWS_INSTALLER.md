# Windows Installer (Setup.exe)

This guide covers building and deploying the **NYC DOT Sidewalk Toolkit** Windows installer produced with [Inno Setup 6](https://jrsoftware.org/isinfo.php).

## What the installer provides

| Item | Location / behavior |
|------|---------------------|
| Application | `{autopf}\NYC DOT Sidewalk Toolkit\` (Program Files, admin install) |
| Executable | `nyc-dot-toolkit.exe` |
| Config templates | `config\` (example profile, role profiles, inquiry templates, budget codes, `.env.example`) |
| Docs | `docs\SIMPLE_START.md`, `docs\GETTING_STARTED.md`, `docs\USER_MANUAL.md`, `INSTALL.txt` |
| Uninstaller | Windows **Apps & features** / Start Menu |

Secrets (real `.env` files) are **not** bundled.

## Prerequisites (build machine)

1. **Windows 10/11** (x64)
2. **Python 3.9–3.12** with pip
3. **Inno Setup 6** — download: https://jrsoftware.org/isdl.php  
   - Optional: add `ISCC.exe` to PATH, or use default `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

## Build Setup.exe

From the repository root:

```powershell
pip install -e ".[postgres,xlsx]"
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

The script will:

1. Install the package with `postgres` and `xlsx` extras
2. Run `python scripts\build_exe.py` if `dist\nyc-dot-toolkit.exe` is missing
3. Compile `installer\nyc_dot_toolkit.iss` with Inno Setup

**Output:** `installer\output\NYC-DOT-Sidewalk-Toolkit-Setup.exe`

Manual steps (equivalent):

```powershell
python scripts\build_exe.py
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" installer\nyc_dot_toolkit.iss
```

## Install on end-user PCs

1. Run `NYC-DOT-Sidewalk-Toolkit-Setup.exe` (UAC prompt for Program Files).
2. Optional checkboxes:
   - **Run setup wizard** — non-interactive wizard (`wizard --non-interactive --skip-checks`); uses environment variables if already set.
   - **Register weekly Analyst Pack** — Task Scheduler job **NYC DOT Analyst Pack** (Sunday 11:00 PM).
   - **Desktop shortcut** — opens Getting Started.
3. By default, **Getting Started** opens when setup finishes.

### Start Menu shortcuts

| Shortcut | Action |
|----------|--------|
| Getting Started | `docs\GETTING_STARTED.md` |
| NYC DOT Toolkit Setup Wizard | `nyc-dot-toolkit.exe wizard` |
| Run Analyst Pack | `nyc-dot-toolkit.exe analyst run --profile config\analyst_profile.yaml` |
| Open Dashboard | `launch_dashboard.bat` → `dash` subcommand or Getting Started |
| User Manual | `docs\USER_MANUAL.md` |

On first install, `config\analyst_profile.yaml` is copied from `analyst_profile.example.yaml` if missing.

## Silent / unattended install

```text
NYC-DOT-Sidewalk-Toolkit-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
NYC-DOT-Sidewalk-Toolkit-Setup.exe /SILENT /DIR="D:\NYC-DOT-Toolkit"
NYC-DOT-Sidewalk-Toolkit-Setup.exe /VERYSILENT /TASKS="runwizard,scheduledtask,desktopicon"
NYC-DOT-Sidewalk-Toolkit-Setup.exe /VERYSILENT /NOTASKS="runwizard"
```

| Flag | Meaning |
|------|---------|
| `/VERYSILENT` | No UI |
| `/SILENT` | Minimal UI |
| `/DIR=` | Custom install folder |
| `/TASKS=` | Comma-separated optional tasks: `runwizard`, `scheduledtask`, `desktopicon` |
| `/NOTASKS=` | Exclude tasks |
| `/LOG=` | Write install log |

Set environment variables **before** silent install if you use `runwizard` (non-interactive), e.g. `SOCRATA_APP_TOKEN`, `PG_DSN`, `DATA_DIR`, `OUTPUT_DIR`.

## Task Scheduler

### During setup

Enable **Register weekly Analyst Pack in Task Scheduler**.

### After install (manual)

```powershell
cd "C:\Program Files\NYC DOT Sidewalk Toolkit"
powershell -ExecutionPolicy Bypass -File .\register_scheduled_task.ps1 -AppDir .
```

Customize:

```powershell
.\register_scheduled_task.ps1 -AppDir "C:\Program Files\NYC DOT Sidewalk Toolkit" `
  -DayOfWeek Monday -Time "06:30"
```

Remove:

```powershell
.\register_scheduled_task.ps1 -AppDir . -Remove
```

Default task: **NYC DOT Analyst Pack** — weekly **Sunday 23:00**, runs:

```text
nyc-dot-toolkit.exe analyst run --profile "…\config\analyst_profile.yaml"
```

## Executable subcommands (installed)

```text
nyc-dot-toolkit.exe wizard [--non-interactive] [--root DIR]
nyc-dot-toolkit.exe analyst run --profile config\analyst_profile.yaml
nyc-dot-toolkit.exe dash
nyc-dot-toolkit.exe doctor
```

The Mission Control UI within the PyInstaller binary is limited; the `dash` command attempts to launch:
1. **Primary:** `python app/dash_app.py` (Dash/FastAPI at http://localhost:8011)
2. **Fallback:** `streamlit run app/app.py` (Streamlit at http://localhost:8501)
3. **Otherwise:** Opens Getting Started guide

For full UI with all features, use a dev install (`pip install -e ".[mission]"`) or Docker (see [GETTING_STARTED.md](GETTING_STARTED.md)).

## CI / tests

Installer file checks run in pytest without Inno Setup. To compile in CI:

```powershell
$env:INNO_SETUP = "1"
powershell -File scripts\build_installer.ps1
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ISCC.exe` not found | Install Inno Setup 6; re-run `build_installer.ps1` |
| Missing `dist\nyc-dot-toolkit.exe` | Run `python scripts\build_exe.py` on Windows |
| Analyst task fails | Run Setup Wizard; confirm `config\analyst_profile.yaml` paths |
| Dashboard won't start | Install Python + `pip install -e ".[ui]"` or use Docker |

See also [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
