# Manhattan Mission Control — Windows Build Guide

This directory contains the tools to package the Manhattan Mission Control
Streamlit app as a native Windows desktop application.

There are **two** ways to run it as an app:

| Build | Source | UX |
|-------|--------|-----|
| **Native window** (recommended) | `desktop_app.py` → `MissionControl.exe` | Opens in its own OS window via **pywebview** — no browser tab, no visible localhost URL |
| **Setup wizard** | `launcher.py` → `MissionControlLauncher.exe` | 4-page tkinter wizard: installs deps, collects API keys, then opens the app in the browser |

Both read API keys from `%APPDATA%\ManhattanMissionControl\.env`, so you can
configure once with the wizard and run the native window thereafter.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11 | Must be on `PATH` — [python.org/downloads](https://python.org/downloads) |
| pip | latest | Bundled with Python |
| pywebview | latest | `pip install pywebview` — needed for the native window |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup | 6.x | [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php) |

Install the build/runtime tooling:

```powershell
pip install pyinstaller pywebview
pip install -e ".[mission,postgres,xlsx,desktop]"
```

---

## Running directly (no build required)

**Native desktop window:**

```bat
python standalone\desktop_app.py
```

Boots Streamlit on a free port and renders it in a native window. Requires
`pip install pywebview` and the app deps.

**Setup wizard (browser):**

```bat
python standalone\launcher.py
```

The 4-page wizard opens immediately and installs dependencies on its Install
page. No PyInstaller or Inno Setup needed.

---

## Step-by-step: build the .exe and installer

### 1 — Build the executables

```bat
cd standalone
python build_exe.py
```

`build_exe.py` builds **both** executables with PyInstaller `--onefile
--windowed` into `standalone\dist\`:

- `MissionControl.exe` — native window (bundles pywebview via `--collect-all`)
- `MissionControlLauncher.exe` — setup wizard

Build just one with `--desktop-only` or `--launcher-only`. If
`standalone\icons\icon.ico` exists it is embedded automatically.

### 2 — Verify the executables

```bat
standalone\dist\MissionControl.exe
```

The native window should open and render the 12-tab app directly (no browser).

```bat
standalone\dist\MissionControlLauncher.exe
```

The wizard should open, allow configuration, install dependencies, and
start the Streamlit server.

### 3 — Compile the Inno Setup installer

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

The self-contained installer is written to:

```
standalone\Output\ManhattanMissionControlSetup.exe
```

### 4 — Distribute

Share `ManhattanMissionControlSetup.exe` with end users. The installer:

- Bundles `MissionControl.exe` (native window) and `MissionControlLauncher.exe`
  (setup wizard), plus `app\`, `src\`, `config\`, and `pyproject.toml`.
- Creates a **Start Menu** group with the app + a "Setup" shortcut, and an
  optional **Desktop** shortcut to the native app.
- Runs the configuration wizard once after installation so the user can enter
  API keys before first launch.

---

## File reference

| File | Purpose |
|------|---------|
| `desktop_app.py` | pywebview native-window wrapper — primary app entry |
| `launcher.py` | tkinter 4-page setup/config wizard |
| `build_exe.py` | PyInstaller build script (builds both exes) |
| `installer.iss` | Inno Setup 6 script |
| `icons/icon.ico` | Application icon (optional) |

---

## API keys

| Key | Where to get it |
|-----|----------------|
| `SOCRATA_APP_TOKEN` | https://data.cityofnewyork.us/profile/app_tokens |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `OLLAMA_HOST` | URL of your local Ollama server, e.g. `http://localhost:11434` |

Keys are saved to `%APPDATA%\ManhattanMissionControl\.env` — never committed
to git. Sensitive fields are masked with `*` in the UI and can be revealed
with the "Show" checkbox on the Configuration page.
