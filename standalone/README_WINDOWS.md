# Manhattan Mission Control — Windows Build Guide

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11 | https://python.org/downloads |
| PyInstaller | latest | `pip install pyinstaller` |
| Inno Setup | 6.x | https://jrsoftware.org/isdl.php |

## Running without building (development)

```bat
cd nyc_data
pip install -e ".[mission,postgres,xlsx]"
python standalone\launcher.py
```

The wizard will open, let you configure API keys, and launch the app.

## Building the .exe

```bat
cd nyc_data\standalone
python build_exe.py
```

This produces `standalone\dist\MissionControlLauncher.exe` (~5 MB).

## Building the installer

1. Open Inno Setup Compiler
2. File → Open → select `standalone\installer.iss`
3. Build → Compile (or press F9)

Output: `standalone\dist\ManhattanMissionControlSetup.exe`

## What the installer does

- Copies `MissionControlLauncher.exe` + all app files to `Program Files\ManhattanMissionControl\`
- Creates Start Menu and Desktop shortcuts
- Launches the configuration wizard on first run

## API keys

| Key | Where to get it |
|-----|----------------|
| `SOCRATA_APP_TOKEN` | https://data.cityofnewyork.us/profile/app_tokens |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

Keys are stored in `%APPDATA%\ManhattanMissionControl\.env` — never committed to git.
