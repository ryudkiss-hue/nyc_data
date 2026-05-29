# Manhattan Mission Control — Electron Desktop App

The richest, most powerful way to run Mission Control on the desktop: a native
**Electron** shell wrapping the self-contained `mission_control_v2` SPA. No
Streamlit, **no Python runtime required** for the core app — the SPA talks to
Socrata, OpenAI, and Gemini directly. This produces a true standalone installer
(`.exe` / `.dmg` / AppImage) with native menus, system tray, persisted window
state, and **auto-update**.

```
┌─────────────────────────────────────────────┐
│ Electron main process (main.js)              │
│  • secure BrowserWindow (contextIsolation)   │
│  • native menu + system tray                 │
│  • auto-updater (GitHub releases)            │
│  • optional Python FastAPI sidecar           │
│      └─ renderer/index.html  ← the SPA       │
└─────────────────────────────────────────────┘
```

## Why this over the Streamlit wrappers?

| | Streamlit + pywebview | This (Electron) |
|---|---|---|
| Python required to run | ✅ yes | ❌ no (SPA is client-side) |
| Native menus / tray / notifications | limited | ✅ full |
| Auto-update | none | ✅ electron-updater |
| Signed cross-platform installers | basic | ✅ electron-builder |
| Self-contained `.exe` | hard (heavy deps) | ✅ clean |

## Prerequisites

- **Node.js 18+** and npm — [nodejs.org](https://nodejs.org)
- (Optional) icons in `build/` — see `build/README.md`

## Develop

```bash
cd desktop
npm install
npm start          # copies the SPA, launches Electron in dev
```

In dev the app loads the canonical SPA directly from
`../app/static/mission_control_v2.html`, so edits there show up on reload
(View → Reload).

## Build installers

```bash
npm run dist          # current OS
npm run dist:win      # Windows NSIS installer (.exe)
npm run dist:mac      # macOS .dmg
npm run dist:linux    # Linux AppImage
```

Output lands in `desktop/dist/`. The `predist` hook copies the SPA into
`renderer/index.html` (single source of truth — never edit that file directly).

## Auto-update

`electron-updater` is wired to GitHub releases (`ryudkiss-hue/nyc_data`).
Publish a release with the built artifacts and installed clients will update
automatically on next launch. To publish from CI:

```bash
GH_TOKEN=… npm run dist -- --publish always
```

## Optional Python sidecar (advanced)

The SPA is fully client-side, but if you want the heavy Python analytics
(PyMC Bayesian, Prophet) exposed to a future SPA panel, the main process can
spawn the FastAPI backend (`socrata_toolkit.api:app`) as a sidecar:

```bash
MMC_SIDECAR=1 MMC_PYTHON=python npm start
```

This requires the Python deps installed (`pip install -e ".[mission]"`) and is
**off by default** — the desktop app runs fully without it.

## Security

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`
- The renderer reaches the OS only through the audited `window.missionControl`
  bridge in `preload.js`
- All external links open in the system browser, never in-app
