# 🚀 Getting Started

There are three ways to use Manhattan Mission Control. Pick the one that fits your situation.

---

## Option 1: Browser App (Zero Install) ⭐ Recommended

> **Best for:** Anyone who wants to explore NYC data right now without installing anything.

**Just open this link:**

> ## 🌐 [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)

That's it. The app runs entirely in your browser. No account. No download. No configuration.

### First 5 minutes in the browser app

1. **Search** — Type a topic in the search box (try "sidewalk", "311", "parking violations")
2. **Browse results** — Click any card to see a preview of the data
3. **Add to Cart** — Click the cart icon to collect datasets for comparison
4. **Query** — Click **SOQL Studio** to write a live SQL-like query against any dataset
5. **Export** — Use the **Export** menu to download as CSV, JSON, Markdown, or Jupyter notebook

> 💡 **Tip:** Press `?` or click the **❓ Help** button in the top-right for the full interactive tutorial.

---

## Option 2: Run the Dashboard Locally

> **Best for:** NYC DOT analysts who need the full Streamlit backend with live ingestion and agency workflows.

### Prerequisites

- Python 3.9 or newer
- pip

### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data

# 2. Install dependencies
pip install -e ".[mission,postgres,xlsx]"

# 3. (Optional) Set up your Socrata token for higher API limits
cp .env.example .env
# Open .env in a text editor and set:
# SOCRATA_APP_TOKEN=your_token_here

# 4. Launch the dashboard
PYTHONPATH=. streamlit run app/app.py
```

### Open the app

Navigate to **http://localhost:8501** in your browser.

> **No token?** No problem! The app automatically enters **Demo Mode** and loads sample data. You'll see a blue "Demo Mode" badge in the header.

### What you'll see

The sidebar on the left lets you navigate between:
- **🏠 Home** — Onboarding, status summary
- **📊 Analyst Workflows** — Choose from 5 workflow views
- **📤 Publish & Pack** — Export reports, send emails
- **⚙️ Settings** — Readiness score, health checks, cache management

---

## Option 3: Cloud Deploy (One Click)

> **Best for:** Sharing the dashboard with a team, or running a persistent hosted version.

### Render.com (Recommended — Free Tier Available)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)

1. Click the button above
2. Sign in to Render.com (or create a free account)
3. Set `SOCRATA_APP_TOKEN` in the Environment Variables section
4. Click **Apply** — deployment takes ~3 minutes
5. Your app will be live at a `*.onrender.com` URL

### Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data)

### Docker

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
docker compose up
# App at http://localhost:8501
```

Full cloud deployment documentation: [[Deployment-Guide]]

---

## First Steps in the Agency Dashboard

Once you're running the Streamlit app, here's a suggested workflow:

### Day 1
1. Go to **Settings → Health** to verify your environment is configured correctly
2. Check **Settings → Readiness** — aim for a score ≥ 80
3. Open **Workflows → QA/QC** and scan the Inventory Ledger

### Daily workflow
1. **Workflows → QA/QC** — Review new defects and status changes
2. **Workflows → Contract** — Check clearance status for active contracts
3. **Workflows → Productivity** — Monitor inspector completion rates
4. **Publish** — Export daily summary (dry-run mode by default)

---

## Next Steps

- 📖 [[Feature-Reference]] — Learn every feature in the browser app
- 🔍 [[SOQL-Guide]] — Write custom queries to filter and analyze data
- 💻 [[Code-Generation]] — Generate Python, R, and JS code snippets
- 🔑 [[API-Keys-Setup]] — Set up your Socrata API token
- 🚀 [[Deployment-Guide]] — Deploy to the cloud

---

*[[Home]] · [[Feature-Reference]] · [[SOQL-Guide]] · [[Deployment-Guide]]*
