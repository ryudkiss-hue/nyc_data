"""
Airflow Plugins for NYC DOT Sidewalk Inspection Orchestration.

Custom operators and sensors:
- SocrataFetchOperator: Incremental fetch from Socrata API
- DataQualityCheckOperator: Phase 1 validation rule execution
- SchemaComplianceOperator: Schema drift detection
- PostgresUpsertOperator: Idempotent UPSERT with checkpoint management
- FreshnessUpdateOperator: Phase 2 freshness tracking
- MetricsEmitterOperator: Phase 2 Prometheus metrics emission
- FreshnessCheckSensor: Wait for data to be fresh
- DataQualitySensor: Wait for upstream quality gates
"""

from custom_operators import (
    DataQualityCheckOperator,
    DataQualitySensor,
    FreshnessCheckSensor,
    FreshnessUpdateOperator,
    MetricsEmitterOperator,
    PostgresUpsertOperator,
    SchemaComplianceOperator,
    SocrataFetchOperator,
)

__all__ = [
    "SocrataFetchOperator",
    "DataQualityCheckOperator",
    "SchemaComplianceOperator",
    "PostgresUpsertOperator",
    "FreshnessUpdateOperator",
    "MetricsEmitterOperator",
    "FreshnessCheckSensor",
    "DataQualitySensor",
]
