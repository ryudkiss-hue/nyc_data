# Master Documentation Index

**Last Updated:** 2026-06-17 | **Status:** Phase 1 Complete ✅

---

## 🎯 Start Here (New Users)

1. **[START_HERE.md](START_HERE.md)** — 5-minute overview + quick start + learning path
2. **[QUICKSTART.md](QUICKSTART.md)** — Installation & setup guide
3. **[README.md](README.md)** — Full project overview & features

---

## 🚀 Deployment & Operations

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** — GitHub Pages + Cloud Run setup
- **[CLAUDE.md](../CLAUDE.md)** — Development patterns & CLI reference
- **[.github/workflows/](../.github/workflows/)** — CI/CD automation

---

## 📦 Architecture & Design (Phase 1)

- **[EXPANDED_METRIC_CHART_REGISTRY.md](EXPANDED_METRIC_CHART_REGISTRY.md)** — 51 Metrics + 45 chart types (primary reference)
- **[METRIC_REGISTRY_COMPREHENSIVE_DESIGN.md](../METRIC_REGISTRY_COMPREHENSIVE_DESIGN.md)** — Phase 1 architecture
- **[PHASE_1_SPECIFICATION.md](../PHASE_1_SPECIFICATION.md)** — Implementation spec

---

## 👤 Solo Development

- **[SOLO_DEVELOPER_GUIDE.md](SOLO_DEVELOPER_GUIDE.md)** — Workflow, permissions, decision log
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Code standards

---

## 📊 Project Documentation

- **[CHANGELOG.md](CHANGELOG.md)** — Version history
- **[TASK_COMPLETION_SUMMARY.md](TASK_COMPLETION_SUMMARY.md)** — Project status
- **[MANIFEST.md](MANIFEST.md)** — Complete file inventory
- **[DOCUMENTATION_MIGRATION_GUIDE.md](DOCUMENTATION_MIGRATION_GUIDE.md)** — File reorganization details

---

## 🔒 Governance & Compliance

- **[SECURITY.md](SECURITY.md)** — Security policies & best practices

---

## 📚 Reference

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** — Pre-deployment verification

---

## 🆘 Troubleshooting

**Missing requirements.txt?**
→ Files reorganized but CI expects them in root. Copy from `00_CONFIG/`

**Module not found errors?**
→ Set `PYTHONPATH=src:.` and ensure you're using the right Python environment

**Tests failing?**
→ Check [START_HERE.md](START_HERE.md) Troubleshooting section

**Documentation out of sync?**
→ Files exist in both root and `00_DOCUMENTATION/` for compatibility. Both are current.

---

## 📍 Directory Structure

```
00_DOCUMENTATION/  (Master documentation)
├── START_HERE.md ⭐ (READ THIS FIRST)
├── README.md
├── QUICKSTART.md
├── DEPLOYMENT_GUIDE.md (NEW)
├── CLAUDE.md
├── EXPANDED_METRIC_CHART_REGISTRY.md
├── SOLO_DEVELOPER_GUIDE.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── TASK_COMPLETION_SUMMARY.md
├── MANIFEST.md
├── DOCUMENTATION_MIGRATION_GUIDE.md
├── DEPLOYMENT_CHECKLIST.md
└── MASTER_DOCUMENTATION_INDEX.md (this file)

Root/ (Compatibility copies)
├── README.md
├── QUICKSTART.md
├── CLAUDE.md
├── DEPLOYMENT_CHECKLIST.md
└── ... (essential files only)
```

---

## ✅ What's Documented

- ✅ Project overview & architecture
- ✅ Installation & quick start (5 min)
- ✅ Deployment (GitHub Pages + Cloud Run)
- ✅ 51 Metric definitions with chart mappings
- ✅ Development workflow & permissions
- ✅ CI/CD automation
- ✅ Troubleshooting guide
- ✅ Phase 1 completion status
- ✅ Phase 2-5 roadmap

---

## 📞 Questions?

Check the relevant section above, or:
- **Setup issues** → QUICKSTART.md
- **Development** → CLAUDE.md + SOLO_DEVELOPER_GUIDE.md
- **Deployment** → DEPLOYMENT_GUIDE.md
- **Metrics** → EXPANDED_METRIC_CHART_REGISTRY.md
- **Architecture** → METRIC_REGISTRY_COMPREHENSIVE_DESIGN.md

---

**Status:** All documentation synchronized | Phase 1 complete | Ready for GitHub Pages publication
