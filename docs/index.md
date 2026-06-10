# NYC DOT Manhattan Mission Control — Docs

> 🌐 **Live App:** [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/) — zero install, browser only

---

## Start Here

| I want to… | Go to |
|-----------|-------|
| Use the browser app | [GitHub Pages](https://ryudkiss-hue.github.io/nyc_data/) |
| Set up locally | [GETTING_STARTED.md](GETTING_STARTED.md) |
| Quick plain-language guide | [SIMPLE_START.md](SIMPLE_START.md) |
| Agency daily operations | [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) |
| Deploy to the cloud | [DEPLOY_CLOUD.md](DEPLOY_CLOUD.md) |
| Full wiki | [../wiki/](../wiki/) |

---

## Mission Control (V2)

- **App overview**: [MISSION_CONTROL.md](MISSION_CONTROL.md)
- **Browser app**: [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/) (GitHub Pages)
- **Agency dashboard**: `PYTHONPATH=. streamlit run app/app.py`

---

## Guided Workflow

1. **Setup**: [GETTING_STARTED.md](GETTING_STARTED.md) → [USER_MANUAL.md](USER_MANUAL.md)
2. **Agency ops**: [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) → `python main.py`
3. **Analyst pack**: `socrata analyst run --profile config/analyst_profile.yaml`
4. **Publish**: [PUBLISHING.md](PUBLISHING.md) (dry-run by default)
5. **Quality check**: `socrata readiness` (target ≥ 95) → [QUALITY_SCORECARD.md](QUALITY_SCORECARD.md)
6. **Cloud deploy**: [DEPLOY_CLOUD.md](DEPLOY_CLOUD.md) → Render / Heroku / Docker

---

## Wiki (Full Documentation)

| Wiki Page | Content |
|-----------|---------|
| [../wiki/Home.md](../wiki/Home.md) | Overview & quick links |
| [../wiki/Getting-Started.md](../wiki/Getting-Started.md) | First steps (browser, local, cloud) |
| [../wiki/Feature-Reference.md](../wiki/Feature-Reference.md) | Every feature explained |
| [../wiki/SOQL-Guide.md](../wiki/SOQL-Guide.md) | SOQL query language reference |
| [../wiki/Code-Generation.md](../wiki/Code-Generation.md) | Python, R, JS, Jupyter code gen |
| [../wiki/Deployment-Guide.md](../wiki/Deployment-Guide.md) | Render, Heroku, Docker, Pages |
| [../wiki/API-Keys-Setup.md](../wiki/API-Keys-Setup.md) | Socrata tokens + env config |
| [../wiki/Troubleshooting.md](../wiki/Troubleshooting.md) | Common errors + fixes |
| [../wiki/Architecture.md](../wiki/Architecture.md) | Codebase structure |
| [../wiki/Changelog.md](../wiki/Changelog.md) | Version history |
| [../wiki/Glossary.md](../wiki/Glossary.md) | Key terms |

---

## Reference Docs

| Doc | Use when |
|-----|----------|
| [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | CLI cheat sheet |
| [API_REFERENCE.md](API_REFERENCE.md) | SOQL + Socrata API |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Errors and logs |
| [FAQ.md](FAQ.md) | Frequently asked questions |
| [COMPLETENESS.md](COMPLETENESS.md) | Agency sign-off checklist |
| [METRICS_GLOSSARY.md](METRICS_GLOSSARY.md) | KPI definitions |
| [USER_MANUAL.md](USER_MANUAL.md) | Full feature reference |

---

## Operations

| Doc | Use when |
|-----|----------|
| [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) | Daily agency operations |
| [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) | Go-live checklist |
| [DEPLOY_CLOUD.md](DEPLOY_CLOUD.md) | Cloud deployment |
| [DOCKER_LOCAL.md](DOCKER_LOCAL.md) | Docker setup |
| [PUBLISHING.md](PUBLISHING.md) | Email, Teams, S3, PDF |

---

## Platform-Specific

| Doc | Content |
|-----|---------|
| [WINDOWS_INSTALLER.md](WINDOWS_INSTALLER.md) | Windows .exe installer |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Docker configuration |
| [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) | AWS infrastructure |
| [MICROSOFT_365_INTEGRATION.md](MICROSOFT_365_INTEGRATION.md) | M365/Teams |
| [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) | GitHub Actions secrets |
