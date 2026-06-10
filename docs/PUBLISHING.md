# Publishing Analyst Packs

Publishing turns a completed pack folder (under `outputs/analyst_pack/YYYY-MM-DD/`) into **shared artifacts**: file shares, BI staging drops, Teams notifications, email summaries, and optional PPTX exports.

## Quick start

1) Create a publish profile:

- Copy `config/publish_profile.example.yaml` to `config/publish_profile.yaml`
- Keep secrets out of YAML; use environment variables for credentials/webhooks.

2) Dry-run a publish:

```bash
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD --dry-run
```

3) Apply publish:

```bash
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD
```

Alias:

```bash
socrata publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD
```

## Multi-profile presets (Dash-friendly)

If you use profiles, you can store multiple publish presets under:

- `config/profiles/<name>/publish_presets/*.yaml`

The Dash **Publish** page will show these presets in a dropdown and will use the selected preset path when publishing.

## Publish profile destinations

### File copy (share drive)

Copies the entire pack folder to `<dest_root>/<pack_name>/...`.

```yaml
file_copy:
  enabled: true
  dest_root: "Z:/Sidewalk/AnalystPacks"
```

### BI export (staging folder)

Copies a BI-friendly subset to `<dest_root>/<pack_name>/...`.

```yaml
bi_export:
  enabled: true
  dest_root: "Z:/Sidewalk/BI/Staging/analyst_pack"
  include:
    - program_kpi.json
    - contract_analytics.json
    - construction_list.xlsx
```

### Teams webhook

Uses a Teams Incoming Webhook URL from an env var.

```yaml
teams:
  enabled: true
  webhook_env: "TOOLKIT_TEAMS_WEBHOOK"
```

### Email (SMTP)

Uses SMTP host/port and reads credentials from env vars.

```yaml
email:
  enabled: true
  smtp:
    host: "smtp.office365.com"
    port: 587
    starttls: true
    username_env: "TOOLKIT_SMTP_USERNAME"
    password_env: "TOOLKIT_SMTP_PASSWORD"
  from_env: "TOOLKIT_SMTP_FROM"
  to: ["manager@example.org"]
```

### PowerPoint export (optional)

Install optional extra:

```bash
pip install -e ".[pptx]"
```

Then enable `pptx:` in the publish profile and point to a `.pptx` template. Placeholder replacement is simple “token in text box” substitution.

Recommended template location:

- `config/pptx_templates/`

## Workflow integration

You can enable publish to run automatically after pack generation by adding this to your analyst profile:

```yaml
steps:
  publish: true
  publish_profile: config/publish_profile.yaml
```

The most recent pack/publish selection is persisted for Dash “Resume” UX in:

- global: `outputs/.state/last_pack.json`
- per-profile: `outputs/.state/profiles/<name>/last_pack.json`

