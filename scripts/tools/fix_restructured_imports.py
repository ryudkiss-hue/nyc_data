import re
from pathlib import Path

# Mapping of old module names (without .py) to (subpackage, new_module_name)
MAPPING = {
    # Quality
    "quality_anomalies": ("quality", "anomalies"),
    "quality_catalog": ("quality", "catalog"),
    "quality_expectations": ("quality", "expectations"),
    "quality_integration": ("quality", "integration"),
    "quality_profiler": ("quality", "profiler"),
    "quality_reports": ("quality", "reports"),
    "quality_rules": ("quality", "rules"),
    "quality_sla": ("quality", "sla"),
    "quality_validator": ("quality", "validator"),
    "validation": ("quality", "validation"),
    "freshness": ("quality", "freshness"),
    "sla_tracking": ("quality", "sla_tracking"),
    # Observability
    "observability_dashboards": ("observability", "dashboards"),
    "observability_health": ("observability", "health"),
    "observability_integration": ("observability", "integration"),
    "observability_logging": ("observability", "logging"),
    "observability_metrics": ("observability", "metrics"),
    "observability_sla": ("observability", "sla"),
    "observability_tracing": ("observability", "tracing"),
    "observability": ("observability", "manager"),
    # Lineage
    "lineage_core": ("lineage", "core"),
    "lineage_impact": ("lineage", "impact"),
    "lineage_persistence": ("lineage", "persistence"),
    "lineage_query": ("lineage", "query"),
    "lineage_tracking": ("lineage", "tracking"),
    "lineage_visualization": ("lineage", "visualization"),
    "lineage": ("lineage", "manager"),
    # Entity
    "entity_blocking": ("entity", "blocking"),
    "entity_incremental": ("entity", "incremental"),
    "entity_matching": ("entity", "matching"),
    "entity_reconciliation": ("entity", "reconciliation"),
    "entity_relationships": ("entity", "relationships"),
    "entity_review": ("entity", "review"),
    # Material
    "material_compliance": ("material", "compliance"),
    "material_definitions": ("material", "definitions"),
    "material_standards": ("material", "standards"),
    # Spatial
    "spatial_analytics": ("spatial", "analytics"),
    "spatial_database": ("spatial", "database"),
    "spatial_metrics": ("spatial", "metrics"),
    "spatial_queries": ("spatial", "queries"),
    "spatial_visualization": ("spatial", "visualization"),
    "spatial": ("spatial", "core"),
    # CDC
    "cdc_compliance": ("cdc", "compliance"),
    "cdc_engine": ("cdc", "engine"),
    "cdc_export": ("cdc", "export"),
    # Dataverse
    "dataverse_connector": ("dataverse", "connector"),
    "dataverse_models": ("dataverse", "models"),
    "dataverse_sync": ("dataverse", "sync"),
    "dataverse_webhooks": ("dataverse", "webhooks"),
    # LLM
    "llm_chatbot": ("llm", "chatbot"),
    "llm_duck_bridge": ("llm", "duck_bridge"),
    "llm_sql_engine": ("llm", "sql_engine"),
    # NLP
    "nlp_advanced": ("nlp", "advanced"),
    "nlp_integration": ("nlp", "integration"),
    "text_analytics": ("analysis", "text"),
    # QGIS
    "qgis_compatibility": ("qgis", "compatibility"),
    "qgis_integration": ("qgis", "integration"),
    # Quantum
    "quantum_optimization": ("quantum", "optimization"),
    "quantum_search": ("quantum", "search"),
    # Reports
    "pdf_reports": ("reports", "pdf"),
    "project_analyst_reports": ("reports", "analyst"),
    "reporting": ("reports", "reporting"),
    # Geo
    "arcgis_integration": ("geo", "arcgis"),
    "mobile_gis": ("geo", "mobile_gis"),
    # Engineering
    "borough_analysis": ("engineering", "borough_analysis"),
    "budget_forecast": ("engineering", "budget_forecast"),
    "construction_list": ("engineering", "construction_list"),
    "contract_analytics": ("engineering", "contract_analytics"),
    "contractor_scorecards": ("engineering", "contractor_scorecards"),
    "cost_estimator": ("engineering", "cost_estimator"),
    "dot_sidewalk": ("engineering", "dot_sidewalk"),
    # Core
    "api": ("core", "api"),
    "app": ("core", "app"),
    "cli": ("core", "cli"),
    "client": ("core", "client"),
    "config": ("core", "config"),
    "db_helpers": ("core", "db_helpers"),
    "logging_utils": ("core", "logging_utils"),
    "models": ("core", "models"),
    "persistence": ("core", "persistence"),
    "pipeline": ("core", "pipeline"),
    "state": ("core", "state"),
    "utils": ("core", "utils"),
    "master_data": ("core", "master_data"),
    "exporters": ("core", "exporters"),
    # Alerts
    "alerts": ("alerts", "manager"),
    "alert_delivery": ("alerts", "delivery"),
    "notification_rules": ("alerts", "rules"),
    "messaging": ("alerts", "messaging"),
    # Analysis
    "analysis": ("analysis", "core"),
    "analysis_advanced": ("analysis", "advanced"),
    "insights_engine": ("analysis", "insights"),
    "metrics": ("analysis", "metrics"),
    "program_metrics": ("analysis", "program"),
    "relevance": ("analysis", "relevance"),
    # Governance
    "compliance": ("governance", "compliance"),
    "audit_trail": ("governance", "audit"),
    "governance": ("governance", "core"),
    "governance_processor": ("governance", "processor"),
    # Integrations
    "bi_integration": ("integrations", "bi"),
    "excel_integration": ("integrations", "excel"),
    "microsoft_graph": ("integrations", "graph"),
    "sql_integration": ("integrations", "sql"),
    # Tools
    "dbeaver_profiles": ("tools", "dbeaver"),
    "install_wizard": ("tools", "wizard"),
    "run_app": ("tools", "runner"),
    "work_management": ("tools", "work"),
    "task_board": ("tools", "tasks"),
    # Viz
    "visualization": ("viz", "core"),
    "plotly_charts": ("viz", "plotly"),
    "dashboard": ("viz", "dashboard"),
    "map_view": ("viz", "map"),
    # Pipeline
    "change_detection": ("pipeline", "cdc"),
    "scd_type2": ("pipeline", "scd"),
    "deduplication": ("pipeline", "dedupe"),
    "soft_delete": ("pipeline", "soft_delete"),
    "streaming_pipeline": ("pipeline", "streaming"),
    "complaint_ingestion": ("pipeline", "complaints"),
    # Discovery
    "schema_registry": ("discovery", "schema"),
    "data_dictionary": ("discovery", "dictionary"),
    "nyc_datasets": ("discovery", "nyc"),
    "search_datasets": ("discovery", "search"),
    # Ops
    "workflow_engine": ("ops", "workflow"),
    "ops": ("ops", "core"),
    # Standards
    "design_rules": ("standards", "design"),
    # SQL
    "conflict": ("sql", "conflict"),
    "query_builder": ("sql", "builder"),
    "temporal_queries": ("sql", "temporal"),
}


def fix_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 1. Fix absolute imports: socrata_toolkit.module -> socrata_toolkit.sub.module
    for old, (sub, new) in MAPPING.items():
        pattern = rf"socrata_toolkit\.{old}\b"
        replacement = f"socrata_toolkit.{sub}.{new}"
        content = re.sub(pattern, replacement, content)

    # 2. Fix relative imports: from .module import ... -> from ..sub.module import ...
    # This is trickier because it depends on the file's current location.
    # Files are now in socrata_toolkit/subpackage/module.py
    # Previously they were in socrata_toolkit/module.py

    # If the file is in a subpackage of socrata_toolkit
    parts = file_path.parts
    if "socrata_toolkit" in parts:
        idx = parts.index("socrata_toolkit")
        if len(parts) > idx + 2:  # it's in a subpackage
            current_sub = parts[idx + 1]

            for old, (sub, new) in MAPPING.items():
                if sub == current_sub:
                    # Same subpackage: from .old -> from .new
                    content = re.sub(rf"from \.{old}\b", f"from .{new}", content)
                    content = re.sub(rf"import \.{old}\b", f"import .{new}", content)
                else:
                    # Different subpackage: from .old -> from ..sub.new
                    content = re.sub(rf"from \.{old}\b", f"from ..{sub}.{new}", content)
                    content = re.sub(rf"import \.{old}\b", f"import ..{sub}.{new}", content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    root = Path(".")
    count = 0

    # Fix files in socrata_toolkit
    for py_file in root.glob("socrata_toolkit/**/*.py"):
        if py_file.name == "__init__.py" and py_file.parent.name == "socrata_toolkit":
            continue  # Handled manually
        if fix_file(py_file):
            count += 1
            print(f"Fixed: {py_file}")

    # Fix files in tests
    for py_file in root.glob("tests/**/*.py"):
        if fix_file(py_file):
            count += 1
            print(f"Fixed: {py_file}")

    print(f"Total files fixed: {count}")


if __name__ == "__main__":
    main()
