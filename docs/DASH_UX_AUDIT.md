# Dash UX audit

## Before (partial rollout)

| Area | Before |
|------|--------|
| Page chrome | Per-page `H1` only; no shared context line or CLI parity |
| Construction / Explore | Sliders fired grid refresh on every tick; no pagination |
| Home | Manifest warnings static at import; pack run blocked UI thread |
| Settings | Credentials only; theme in sidebar not persisted |
| Review | Synchronous `subprocess.run` in callbacks |
| CSS | Dark theme only in practice; no reduced-motion guard |
| Tests | No page import smoke test |

## After (completed rollout)

| Area | After |
|------|--------|
| Shell | `page_shell`, `empty_state`, context line, CLI hints on all analyst pages |
| Construction | 300ms debounce, `dcc.Loading`, 100-row pages + Show more, demo pack |
| Home | Pathname refresh of manifest/artifacts; offline checkbox → `--offline` |
| Settings | Light/dark, font scale, offline toggle, export/import `ui_prefs.json` |
| Review | `background_jobs` for list/save; instant “Saving…” feedback |
| App | Deep links `?page=&pack=`, offline banner, profile dropdown |
| CSS | Shell/empty/skeleton classes, `data-theme=light`, `prefers-reduced-motion` |

## Performance budget

| Interaction | Target |
|-------------|--------|
| Slider → preview update | ≤ 350ms after last movement (300ms debounce + render) |
| Page navigation | First paint < 2s on LAN with cached pack |
| Grid initial slice | 100 rows; “Show more” adds 100 without full re-query |
| Analyst pack / review CLI | Non-blocking; UI stays responsive |
| Doctor / publish | Background thread; poll interval 800–1000ms |

## Checklist

- [x] `page_shell` on Home, Explore, Construction, Contracts, Metrics, Inquiries, Review, Data Trust, Publish, Settings
- [x] Debounced sliders on Construction (and Explore)
- [x] `dcc.Loading` on heavy previews
- [x] Empty states + demo pack entry points
- [x] `ui_prefs.json` theme / font / offline persistence
- [x] Home offline → `socrata analyst run --offline`
- [x] Review subprocess via `background_jobs`
- [x] `tests/test_dash_pages_import.py`
- [x] `docs/DASH_UX_AUDIT.md` (this file)

## Verification

```powershell
python -m pytest tests/test_dash_pages_import.py tests/test_interactive_explore.py -q
python -m pytest tests/ -q
python dash_app/app.py
```

Optional browser smoke: Home → Run pack toggle offline; Explore sliders; Construction Show more; Settings theme toggle.
