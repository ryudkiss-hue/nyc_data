# 🚧 Manhattan Mission Control — Wiki

Welcome to the official documentation wiki for **Manhattan Mission Control**, the NYC DOT open data exploration and agency analytics platform.

---

## 🚀 Quick Links

| I want to… | Go to |
|-----------|-------|
| **Use the browser app right now** | [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/) |
| **Set up the dashboard locally** | [[Getting-Started]] |
| **Learn SOQL queries** | [[SOQL-Guide]] |
| **Generate code from datasets** | [[Code-Generation]] |
| **Deploy to the cloud** | [[Deployment-Guide]] |
| **See all features** | [[Feature-Reference]] |
| **Troubleshoot errors** | [[Troubleshooting]] |
| **Read the changelog** | [[Changelog]] |

---

## 📖 Wiki Pages

### 🟢 For Users
- [[Getting-Started]] — First steps, zero-install browser app, local setup
- [[Feature-Reference]] — Complete guide to every feature
- [[SOQL-Guide]] — Writing queries to filter and analyze data
- [[Code-Generation]] — Generate Python, R, JS, GitHub Actions code

### 🔵 For Developers & Analysts
- [[Deployment-Guide]] — Render.com, Heroku, Docker, GitHub Pages
- [[API-Keys-Setup]] — Socrata tokens, environment configuration
- [[Architecture]] — How the codebase is organized

### 📋 Reference
- [[Changelog]] — Version history and what's new
- [[Troubleshooting]] — Common errors and solutions
- [[Glossary]] — Key terms and definitions

---

## 🌟 What Is Manhattan Mission Control?

Manhattan Mission Control is a **dual-mode platform**:

1. **🌐 Open Data Explorer** — A beautiful, zero-install single-page app that lets anyone search, preview, query, and export data from thousands of NYC open datasets. Just open a browser — no account or installation needed.

2. **🏢 Agency Analytics Dashboard** — A Streamlit-powered backend for NYC DOT SIM analysts with live data ingestion, QA/QC workflows, spatial conflict detection, contract clearance, and productivity tracking.

Both modes are available from the same repository, deployed automatically via GitHub Actions.

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                  Manhattan Mission Control               │
├──────────────────────────┬──────────────────────────────┤
│  🌐 Browser App          │  🏢 Agency Dashboard         │
│  (mission_control_v2.html│  (Streamlit + Python)        │
│   — no server needed)    │   — requires backend)        │
├──────────────────────────┴──────────────────────────────┤
│           Socrata Open Data API (NYC Open Data)          │
│       api.us.socrata.com/api/catalog/v1                  │
└─────────────────────────────────────────────────────────┘
```

---

*Last updated: May 2025 · [Report an issue](https://github.com/ryudkiss-hue/nyc_data/issues)*
