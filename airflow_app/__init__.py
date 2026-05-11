"""
Airflow Package for NYC DOT Sidewalk Inspection Data Orchestration.

This package contains:
- Configuration management (config.py)
- DAG registry and validation (dag_registry.py)
- Custom operators and sensors (plugins/)
- Production-grade DAGs for incident ingestion, repair scheduling, and KPI materialization
- Full integration with Phase 1 (domain model) and Phase 2 (observability)
"""

__version__ = "0.1.0"
__author__ = "NYC DOT Data Engineering"
