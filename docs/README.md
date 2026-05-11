# NYC Sidewalk Data Toolkit - Complete Documentation Index

Welcome to the comprehensive documentation for the NYC Sidewalk Data Toolkit. This directory contains all guides, references, and manuals for the system.

## 🎯 Getting Started (Start Here!)

### New Users
1. **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide to get the toolkit running
2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Deploy to production (Docker, Kubernetes, Cloud)
3. **[README.md](README.md)** - Project overview and architecture

### For Frontend Developers
1. **[../frontend/SETUP.md](../frontend/SETUP.md)** - React frontend setup (Node.js, npm, Vite)
2. **[../frontend/README.md](../frontend/README.md)** - Frontend architecture, components, state management

### For Backend Developers  
1. **[LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md)** - LLM integration (chatbot, SQL queries)
2. **[api_guide.md](api_guide.md)** - REST API documentation

---

## 📚 Feature Documentation

### AI/LLM Features
- **[LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md)** - Complete chatbot and SQL query engine guide
  - Setup (Ollama, OpenAI, Hugging Face)
  - Quick start examples
  - CLI integration
  - API integration
  - Streamlit integration
  - Best practices and troubleshooting

### Data Management
- **[data_quality.md](data_quality.md)** - Data quality checks and validation
- **[entity_resolution.md](entity_resolution.md)** - Entity matching and reconciliation
- **[master_data_management.md](master_data_management.md)** - Master data management patterns
- **[sla_configuration.md](sla_configuration.md)** - SLA setup and monitoring

### Geospatial Features
- **[geospatial.md](geospatial.md)** - Geospatial queries and analysis
- **[spatial_architecture.md](spatial_architecture.md)** - Spatial database design
- **[qgis_field_guide.md](qgis_field_guide.md)** - QGIS integration for field work

### NYC-Specific Content
- **[material_standards.md](material_standards.md)** - Material specifications for NYC streets
- **[ada_compliance_reference.md](ada_compliance_reference.md)** - ADA compliance rules
- **[nyc_street_design_reference.md](nyc_street_design_reference.md)** - NYC street design standards
- **[domain_model.md](domain_model.md)** - NYC business domain model

### Analytics & Reporting
- **[observability.md](observability.md)** - System monitoring and observability
- **[quality_sla.md](quality_sla.md)** - Data quality SLA setup
- **[METRICS_GLOSSARY.md](METRICS_GLOSSARY.md)** - Metric definitions and calculations

---

## 🔧 Operations & Deployment

### Deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment guide
  - Docker setup
  - Docker Compose orchestration
  - Kubernetes deployment
  - Cloud deployment (AWS, Azure, GCP)
  - SSL/TLS configuration

- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Docker-specific setup and commands
- **[api_deployment.md](api_deployment.md)** - API server deployment
- **[airflow_deployment.md](airflow_deployment.md)** - Airflow DAG deployment

### Operations
- **[OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)** - Daily operations and maintenance
- **[RUNBOOKS.md](RUNBOOKS.md)** - Common operational runbooks
- **[observability_dashboard.md](observability_dashboard.md)** - Dashboard setup and usage

### Database & Integration
- **[sql_integration.md](sql_integration.md)** - SQL integration patterns
- **[cdc_guide.md](cdc_guide.md)** - Change Data Capture setup
- **[arcgis_integration.md](arcgis_integration.md)** - ArcGIS integration
- **[MICROSOFT_365_INTEGRATION.md](MICROSOFT_365_INTEGRATION.md)** - M365 sync and integration
- **[POWER_APPS_INTEGRATION.md](POWER_APPS_INTEGRATION.md)** - Power Apps integration

---

## 🔐 Security & Compliance

- **[security.md](security.md)** - Security best practices
- **[api_security.md](api_security.md)** - API authentication and authorization
- **[audit_compliance.md](audit_compliance.md)** - Audit and compliance logging
- **[SECURITY_AND_PACKAGING.md](SECURITY_AND_PACKAGING.md)** - Security hardening and packaging

---

## 📋 Reference & Integration

### API Reference
- **[api_guide.md](api_guide.md)** - REST API endpoints and usage
- **[api_versioning.md](api_versioning.md)** - API versioning strategy
- **[api_governance.md](api_governance.md)** - Data governance through APIs

### Integration Guides
- **[advanced_integrations.md](advanced_integrations.md)** - Advanced integration patterns
- **[INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md)** - Integration verification checklist
- **[INTEGRATION_QUICK_START.md](INTEGRATION_QUICK_START.md)** - Quick integration start
- **[PHASE3_INTEGRATION_GUIDE.md](PHASE3_INTEGRATION_GUIDE.md)** - Phase 3 specific integration

### Pipelines & Workflows
- **[pipelines.md](pipelines.md)** - Data pipeline architecture
- **[airflow_operations.md](airflow_operations.md)** - Airflow DAG management
- **[airflow_migration_guide.md](airflow_migration_guide.md)** - Migration to Airflow

### CLI Usage
- **[cli.md](cli.md)** - CLI command reference
- **[cheatsheet.md](cheatsheet.md)** - Quick reference cheatsheet

---

## 📖 Learning Resources

### Concepts
- **[architecture.md](architecture.md)** - System architecture overview
- **[lineage_architecture.md](lineage_architecture.md)** - Data lineage and DAG design
- **[installation.md](installation.md)** - Installation guide
- **[EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md)** - Executable package structure

### Tutorials
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[testing_ci.md](testing_ci.md)** - Testing and CI/CD setup
- **[temporal_analytics.md](temporal_analytics.md)** - Time-based analysis tutorial
- **[spatial_analytics.md](spatial_analytics.md)** - Geospatial analysis tutorial

### FAQ & Support
- **[sop_faq.md](sop_faq.md)** - Standard operating procedures and FAQ
- **[new-repo-bootstrap.md](new-repo-bootstrap.md)** - Creating new projects from template

---

## 🔍 Finding What You Need

### By Role

**Data Analyst**
1. Start: [QUICKSTART.md](QUICKSTART.md)
2. Learn: [data_quality.md](data_quality.md), [spatial_analytics.md](spatial_analytics.md)
3. Query: [api_guide.md](api_guide.md), [cli.md](cli.md)
4. Reference: [METRICS_GLOSSARY.md](METRICS_GLOSSARY.md), [cheatsheet.md](cheatsheet.md)

**System Administrator**
1. Start: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Setup: [DOCKER_SETUP.md](DOCKER_SETUP.md), [../frontend/SETUP.md](../frontend/SETUP.md)
3. Monitor: [observability.md](observability.md), [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)
4. Troubleshoot: [RUNBOOKS.md](RUNBOOKS.md)

**Backend Developer**
1. Start: [architecture.md](architecture.md), [installation.md](installation.md)
2. Learn: [LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md), [api_guide.md](api_guide.md)
3. Integrate: [advanced_integrations.md](advanced_integrations.md), [pipelines.md](pipelines.md)
4. Deploy: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), [api_deployment.md](api_deployment.md)

**Frontend Developer**
1. Start: [../frontend/SETUP.md](../frontend/SETUP.md), [../frontend/README.md](../frontend/README.md)
2. Learn: [api_guide.md](api_guide.md), [LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md)
3. Deploy: [../frontend/SETUP.md#deployment](../frontend/SETUP.md)

**DevOps/SRE**
1. Start: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Setup: [DOCKER_SETUP.md](DOCKER_SETUP.md), [airflow_deployment.md](airflow_deployment.md)
3. Monitor: [observability.md](observability.md), [observability_dashboard.md](observability_dashboard.md)
4. Secure: [security.md](security.md), [audit_compliance.md](audit_compliance.md)

### By Task

**Install & Setup**
- Local development: [QUICKSTART.md](QUICKSTART.md)
- Production deployment: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- Docker setup: [DOCKER_SETUP.md](DOCKER_SETUP.md)
- Frontend setup: [../frontend/SETUP.md](../frontend/SETUP.md)

**Query Data**
- CLI commands: [cli.md](cli.md) + [cheatsheet.md](cheatsheet.md)
- REST API: [api_guide.md](api_guide.md)
- Natural language: [LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md)
- Spatial queries: [geospatial.md](geospatial.md)

**Integrate Systems**
- Data pipelines: [pipelines.md](pipelines.md)
- Airflow: [airflow_operations.md](airflow_operations.md)
- ArcGIS: [arcgis_integration.md](arcgis_integration.md)
- Microsoft 365: [MICROSOFT_365_INTEGRATION.md](MICROSOFT_365_INTEGRATION.md)
- Advanced: [advanced_integrations.md](advanced_integrations.md)

**Monitor & Troubleshoot**
- System health: [observability.md](observability.md)
- Dashboard: [observability_dashboard.md](observability_dashboard.md)
- Runbooks: [RUNBOOKS.md](RUNBOOKS.md)
- Operations: [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)

**Ensure Quality & Security**
- Data quality: [data_quality.md](data_quality.md)
- SLA setup: [sla_configuration.md](sla_configuration.md)
- Compliance: [audit_compliance.md](audit_compliance.md)
- Security: [security.md](security.md) + [api_security.md](api_security.md)

---

## 📊 Documentation Statistics

| Category | Count | Files |
|----------|-------|-------|
| Getting Started | 3 | QUICKSTART, DEPLOYMENT_GUIDE, README |
| Core Features | 15 | Data quality, entity resolution, geospatial, analytics |
| Deployment | 6 | Docker, Kubernetes, Cloud, API, Airflow |
| Operations | 5 | Operations manual, runbooks, observability, monitoring |
| Integration | 8 | APIs, database, M365, Power Apps, ArcGIS, pipelines |
| Security | 4 | Security, audit, compliance, API security |
| Reference | 8 | CLI, cheatsheet, glossary, API docs, architecture |
| **Total** | **49** | **Complete coverage** |

---

## 🔗 Quick Navigation

### External Resources
- [GitHub Repository](https://github.com/ryudkiss-hue/nyc_data)
- [Main README](../README.md)
- [Frontend Documentation](../frontend/README.md)
- [Project Examples](../examples/)

### Important Sections
- **Installation**: [QUICKSTART.md](QUICKSTART.md) → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **CLI Reference**: [cli.md](cli.md) → [cheatsheet.md](cheatsheet.md)
- **API Reference**: [api_guide.md](api_guide.md) → [LANGCHAIN_INTEGRATION_GUIDE.md](LANGCHAIN_INTEGRATION_GUIDE.md)
- **Operations**: [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) → [RUNBOOKS.md](RUNBOOKS.md)

---

## 📞 Support & Feedback

For questions, issues, or documentation improvements:
1. Check [sop_faq.md](sop_faq.md) for common questions
2. Review [RUNBOOKS.md](RUNBOOKS.md) for operational issues
3. Submit issues to [GitHub Issues](https://github.com/ryudkiss-hue/nyc_data/issues)

---

**Last Updated**: 2026-05-11  
**Version**: 3.0  
**Status**: Complete & Production-Ready
