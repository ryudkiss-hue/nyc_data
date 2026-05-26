# 🚀 Deployment Guide

How to deploy Manhattan Mission Control — both the HTML browser app and the Streamlit agency dashboard.

---

## 🌐 GitHub Pages (HTML App — Automatic)

The standalone HTML app at `app/static/mission_control_v2.html` is automatically deployed to GitHub Pages on every push to `main`.

**Live URL:** [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)

### How it works

The workflow in `.github/workflows/pages.yml`:

1. Checks out the repository
2. Copies `mission_control_v2.html` → `_site/index.html`
3. Uploads as a GitHub Pages artifact
4. Deploys to GitHub Pages

### Enabling GitHub Pages (one-time setup)

1. Go to your repo on GitHub → **Settings → Pages**
2. Set **Source** to **GitHub Actions**
3. Save — the next push to `main` will deploy

### Manually re-trigger deployment

```bash
# Push any change to main to trigger the workflow
git commit --allow-empty -m "chore: retrigger pages deploy"
git push origin main
```

Or go to **Actions → Deploy Mission Control to GitHub Pages → Run workflow**.

---

## 🟢 Render.com (Streamlit Dashboard — Recommended)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)

### One-click deploy

1. Click the button above
2. Sign in to [Render.com](https://render.com) (free account OK)
3. The `render.yaml` blueprint is auto-detected
4. Set environment variables (see below)
5. Click **Apply** — builds and deploys in ~3 minutes

### Environment Variables on Render

| Variable | Required | Description |
|----------|----------|-------------|
| `SOCRATA_APP_TOKEN` | Optional | Socrata API token (omit for demo mode) |
| `PYTHONPATH` | **Required** | Must be set to `.` |
| `PYTHON_VERSION` | Auto | Set to `3.11.9` by blueprint |
| `MISSION_DEMO` | Optional | Set to `1` to force demo mode |

> ⚠️ **Important:** `PYTHONPATH=.` **must** be set. The `render.yaml` blueprint sets this automatically. Without it, you'll get `ModuleNotFoundError: No module named 'app'`.

### render.yaml (already in repo)

```yaml
services:
  - type: web
    name: nyc-mission-control
    runtime: python
    plan: free
    buildCommand: pip install -e ".[mission,postgres,xlsx]"
    startCommand: >
      PYTHONPATH=. python -m streamlit run app/app.py
      --server.port=$PORT
      --server.address=0.0.0.0
      --server.headless=true
    healthCheckPath: /
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.9"
      - key: PYTHONPATH
        value: "."
      - key: MISSION_DEMO
        value: "1"
      - key: SOCRATA_APP_TOKEN
        sync: false
```

### Troubleshooting Render Deployments

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'app'` | `PYTHONPATH` not set to `.` | Add `PYTHONPATH=.` in Environment Variables |
| `No module named 'streamlit'` | Wrong extra in buildCommand | Use `pip install -e ".[mission]"` |
| Build timeout | Large dependencies | Use Render's paid plan for longer build time |
| Port error | Wrong port binding | Ensure `--server.port=$PORT` in start command |

---

## 🟣 Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data)

### Manual Heroku Deploy

```bash
# Install Heroku CLI
brew install heroku/brew/heroku   # macOS
# or: https://devcenter.heroku.com/articles/heroku-cli

# Login and create app
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set PYTHONPATH=.
heroku config:set SOCRATA_APP_TOKEN=your_token_here

# Deploy
git push heroku main

# Open the app
heroku open
```

### Procfile (already in repo)

```
web: PYTHONPATH=. python -m streamlit run app/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
```

---

## 🐳 Docker

### Quick start

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data

# Start the dashboard
docker compose up

# App available at http://localhost:8501
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - PYTHONPATH=.
      - SOCRATA_APP_TOKEN=${SOCRATA_APP_TOKEN:-}
      - MISSION_DEMO=${MISSION_DEMO:-1}
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
```

### Build and run manually

```bash
docker build -t nyc-mission-control .
docker run -p 8501:8501 \
  -e PYTHONPATH=. \
  -e SOCRATA_APP_TOKEN=your_token \
  nyc-mission-control
```

---

## 🖥️ Local Development

### Prerequisites

- Python 3.9+
- pip

### Setup

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data

# Install with all mission-critical dependencies
pip install -e ".[mission,postgres,xlsx]"

# Copy and configure environment
cp .env.example .env
# Edit .env: SOCRATA_APP_TOKEN=your_token_here

# Launch
PYTHONPATH=. streamlit run app/app.py
```

### Environment variables

```bash
# .env file
SOCRATA_APP_TOKEN=your_token_here
MISSION_DEMO=0              # set to 1 to force demo mode
STREAMLIT_SERVER_PORT=8501  # default port
```

---

## ☁️ Other Platforms

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

Set environment variables in Railway dashboard:
- `PYTHONPATH=.`
- `SOCRATA_APP_TOKEN=your_token`

**Start command:** `PYTHONPATH=. python -m streamlit run app/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true`

### AWS / GCP / Azure

See **[docs/AWS_DEPLOYMENT_GUIDE.md](../docs/AWS_DEPLOYMENT_GUIDE.md)** for full cloud infrastructure deployment.

---

## 🏗️ GitHub Actions CI/CD

The repository includes GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `pages.yml` | Push to `main` | Deploy HTML app to GitHub Pages |
| `ci.yml` (if present) | Push / PR | Run linting and tests |

### Checking deployment status

1. Go to repo → **Actions** tab
2. Click the latest workflow run
3. Check each step's status

---

## 🔑 Socrata API Token

Without a token, the Socrata API rate-limits to ~1 request/second. A free token removes this:

1. Register at [data.cityofnewyork.us](https://data.cityofnewyork.us/)
2. **Developer Settings → Create New App Token**
3. Copy the token

Set it in your deployment:
- **Render:** Environment Variables → `SOCRATA_APP_TOKEN`
- **Heroku:** `heroku config:set SOCRATA_APP_TOKEN=your_token`
- **Docker:** `-e SOCRATA_APP_TOKEN=your_token`
- **Local:** `.env` file → `SOCRATA_APP_TOKEN=your_token`

---

*[[Home]] · [[Getting-Started]] · [[API-Keys-Setup]] · [[Troubleshooting]]*
