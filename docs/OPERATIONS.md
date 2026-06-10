# 🗽 NYC DOT Sidewalk Toolkit — Operations Manual

## 1. Executive Overview

The NYC DOT Sidewalk Data Governance Toolkit is an enterprise data platform optimized for local-first analysis, ensuring 100% data integrity across municipal infrastructure datasets.

### Core Mission
- **Infrastructure Asset Management**: Prioritize repairs using lifecycle tracking (Inspection → Complaint → Contract → QC).
- **Project Coordination**: Identify geographic conflicts using DuckDB Spatial.
- **Administration**: Synthesize "Budget Spent vs. Physical Productivity Achieved" briefings.

### System Health Targets
- **Availability**: 99.5% (Local Workstation)
- **Response Time**: < 2 seconds for analytical queries
- **Data Integrity**: Baseline scan for all 26 registered datasets (Mean, Variance, Skewness, Kurtosis).

---

## 2. Local Deployment & Entry Points

### Python Environment (Development)
```bash
pip install -e ".[mission]"
socrata wizard
python main.py
```

### Docker Stack (Production/Scheduled)
```bash
docker compose --profile analyst up -d postgres
docker compose --profile analyst run --rm setup
docker compose --profile analyst up -d analyst-runner
```

### Windows Standalone (.exe)
```text
dist\nyc-dot-toolkit.exe wizard
dist\nyc-dot-toolkit.exe analyst run --profile config\analyst_profile.yaml
```

---

## 3. Analyst Workflows

### Weekly Analyst Pack
The primary output for DOT operations is the **Analyst Pack**, generated weekly:
```bash
socrata analyst run --profile config/analyst_profile.yaml
```
**Key Artifacts**:
- `construction_list.xlsx`: Prioritized repair locations.
- `conflicts_summary.md`: Permit and capital project conflicts.
- `contract_status.md`: Progress, budget CPI, and productivity metrics.
- `program_kpi.json`: Red/yellow/green program health metrics.

### Review & Decision Support
Decisions are stored in a local DuckDB instance (`outputs/.state/profiles/<name>/decisions.duckdb`):
```bash
socrata review set --kind conflict --key L123 --status resolved --notes "Checked permits"
socrata review export --pack outputs/analyst_pack/YYYY-MM-DD
```

---

## 4. Daily Operations & Runbook

### Morning Checklist (Daily)
1. **Infrastructure Check**: `python launcher.py doctor`
2. **Freshness Verify**: `socrata sync -i erm2-nwe9 --table complaints_311`
3. **Data Integrity Sweep**: Use **Settings & Quality → Readiness** tab in Dash/Streamlit.

### Quality Gates
Target **95+ Readiness Score** before promotion to executive dashboards:
```powershell
socrata readiness
python -m pytest tests/ -m "not legacy"
```

---

## 5. Emergency Procedures

### Incident Response
1. **Assess Severity**: Determine if data ingestion is failing or if analytics are skewed.
2. **Containment**: Isolate corrupt DuckDB partitions.
3. **Recovery**: Restore from daily local backup (`data/local_db/backups/`).
4. **Validation**: Re-run the **Four Moments** integrity scan.

---

## 6. Support & Resources
- **CLI Reference**: [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)
- **Data Discovery**: [DATASETS.md](../DATASETS.md)
- **Ingest Logs**: `../outputs/logs/ingest.jsonl`
- **Schema Drift**: [SCHEMA_DRIFT.md](SCHEMA_DRIFT.md)
