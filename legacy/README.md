# Legacy UIs

The **primary analyst interface** is the Dash app:

```bash
python dash_app/app.py
```

## NiceGUI Mission Control

`nicegui_mission_control.py` is the older 311 / triage / map workspace. It requires `pip install nicegui` (not in the default package install).

Run only when you need it:

```bash
set NYC_DOT_LEGACY_NICEGUI=1
python legacy/nicegui_mission_control.py
```

Or from repo root: `python app.py` (same gate).
