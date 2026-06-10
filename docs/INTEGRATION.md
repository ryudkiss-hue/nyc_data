# 🔗 Integration & API Guide

## 1. Overview
The NYC DOT Sidewalk Toolkit provides multiple integration points for external services, ranging from geospatial GIS sync to automated M365 workflows and AI-driven data exploration.

---

## 2. Python API Reference
All toolkit features are available via the `socrata_toolkit` package.

### Core Patterns
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.analysis import quality_report

# Initialize client
client = SocrataClient(SocrataConfig())

# Fetch and Score
df = client.fetch_dataframe(domain, fourfour)
report = quality_report(df)
print(f"Data Quality: {report.overall}%")
```

---

## 3. External Platform Integrations

### ArcGIS Integration
Connect to NYC's geographic system of record:
- **Authentication**: Uses `ArcGISCredential` with organization URLs.
- **Workflow**: Import street reference data and export local "Hotspot" analysis results to city-wide feature services.

### Microsoft 365 (SharePoint & Outlook)
Automate repair notifications and work orders:
- **SharePoint**: Bi-directional sync between local DuckDB decisions and organization lists.
- **Outlook**: Automated calendar event creation for scheduled repairs with attendee management.

### Power Apps & Power BI
- Use the **FastAPI REST backend** as a custom connector for Power Apps.
- Connect Power BI directly to the **Postgres warehouse** for executive dashboarding.

---

## 4. AI & LangChain Integration
The toolkit includes specialized LLM-driven tools for data exploration:
- **SQL Query Engine**: Natural language to SOQL/SQL translation.
- **Conversational Chatbot**: Context-aware assistance for data quality and analytics.
- **Specialized Assistants**: Automated synthesis of audit findings into management briefings.

---

## 5. Observability Stack
The toolkit integrates with production-grade monitoring:
- **Prometheus**: Real-time metrics collection (pipeline duration, row counts).
- **Grafana**: Pre-configured dashboards for system health and SLA tracking.
- **Jaeger**: Distributed tracing for multi-step ingestion pipelines.

---

## 6. Phase-Based Migration
Integration follows a non-breaking additive pattern:
1. **Phase 1**: Core validation and KPI logic.
2. **Phase 2**: Operational logging and metrics.
3. **Phase 3**: Airflow orchestration and automated scheduling.
4. **Phase 4**: API-first exposure of all materialized views.
