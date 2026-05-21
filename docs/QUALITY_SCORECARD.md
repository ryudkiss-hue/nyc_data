# Quality scorecard — axes to 100

This toolkit targets **100 on every axis** that can be verified locally. Some axes also need agency data, SMTP/Teams paths, and manual sign-off (see COMPLETENESS.md).

## Verify locally

```powershell
socrata doctor --checklist
socrata readiness
python -m pytest tests/test_readiness.py tests/test_dash_pages_import.py -q
streamlit run app/app.py
```

## Axes

| Axis | What “100” means | How we measure |
|------|------------------|----------------|
| **Accessibility** | WCAG-minded: skip link, focus rings, KPI text+icon (not color-only), reduced motion, table captions, `aria-live` toasts | `socrata readiness` + manual keyboard pass |
| **Functionality** | Analyst pack, publish, review, import shims, profiles, demo pack | Doctor + pytest |
| **Presentation / UX** | Socrata ingestion matrix, ROI header, four workflow views | Streamlit smoke + docs/preview |
| **Packaging** | Wizard, installer script, launcher→Streamlit | `scripts/build_installer.ps1`, INSTALL.txt |
| **Reliability** | Background jobs (non-blocking UI), pytest green | `socrata readiness --pytest` |
| **Documentation** | SIMPLE_START, USER_MANUAL, FAQ, ANALYST_WORKFLOW | File presence in readiness |
| **Security** | Secrets in env only, no tokens in logs | Manual + publish dry-run |
| **Performance** | Paginated tables, debounced Explore, pack cache | Load with demo pack |
| **Job fit (SW)** | Role profiles jid-35715 / jid-42159, role KPIs | `config/role_profiles/` + Metrics page |

## Automated vs manual

- **Automated 100%** on an axis = every check in `socrata readiness` for that axis passes.
- **Operational 100%** = your `analyst_profile.yaml` points at real Excel/SQL, publish profile tested with dry-run, and COMPLETENESS.md signed.

## Settings dashboard

Open **Settings → Quality readiness** for live axis bars (same engine as `socrata readiness`).
