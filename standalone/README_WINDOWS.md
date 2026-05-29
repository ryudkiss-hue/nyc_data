# Manhattan Mission Control — Windows Build Guide

This directory contains the tools to package the Manhattan Mission Control
Streamlit app as a native Windows desktop application.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11 | Must be on `PATH` — [python.org/downloads](https://python.org/downloads) |
| pip | latest | Bundled with Python |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup | 6.x | [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php) |

Install PyInstaller before building:

```powershell
pip install pyinstaller
```

---

## Running the launcher directly (no build required)

From the repo root:

```bat
python standalone\launcher.py
```

The 4-page wizard opens immediately. Dependencies are installed on the fly by
the wizard's Install page. No PyInstaller or Inno Setup needed.

---

## Step-by-step: build the .exe and installer

### 1 — Build the executable

```bat
cd standalone
python build_exe.py
```

`build_exe.py` calls PyInstaller with `--onefile --windowed` and writes the
result to `standalone\dist\MissionControlLauncher.exe`.

If `standalone\icons\icon.ico` exists it is embedded automatically;
otherwise the build continues without a custom icon.

### 2 — Verify the executable

```bat
standalone\dist\MissionControlLauncher.exe
```

The wizard should open, allow configuration, install dependencies, and
start the Streamlit server at http://localhost:8501.

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

- Bundles `MissionControlLauncher.exe` plus `app\`, `src\`, `config\`, and
  `pyproject.toml`.
- Creates a **Start Menu** group and an optional **Desktop** shortcut.
- Launches the configuration wizard automatically after installation.

---

## File reference

| File | Purpose |
|------|---------|
| `launcher.py` | tkinter 4-page wizard — the main launcher |
| `build_exe.py` | PyInstaller build script |
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
