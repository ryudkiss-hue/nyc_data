# Analytics Module: Data Quality & Integrity

## Overview
The `quality` module within the `analytics` package provides hardcoded skills for verifying the integrity and statistical soundness of NYC DOT datasets. It bridges the gap between raw Socrata telemetry and executive-level confidence.

## Skills

### 1. DataQualityAudit
Performs an empirical sweep of a dataset to identify statistical anomalies and missingness.
- **Mandatory Reporting**: Calculates the "Four Moments" (Mean, Variance, Skewness, Kurtosis) as required by the project mandate.
- **Outlier Detection**: Identifies records with a Z-score > 3.
- **Null Tracking**: Provides a per-column count of missing values.

**Usage:**
```python
from socrata_toolkit.analytics.quality import DataQualityAudit
skill = DataQualityAudit()
result = skill.run(df=my_dataframe, table_name="inspections")
```

### 2. SchemaMapper
Validates that the local DuckDB storage schema aligns with the authoritative `datasets.yaml` registry.
- **Drift Detection**: Identifies "Extra" columns added via schema evolution during sync.
- **Integrity Check**: Identifies "Missing" columns that are expected but absent.

### 3. MetricReconciliation
Reconciles record counts between the local cache and the Socrata registry metadata.
- **Drift Logging**: Any delta discovered is logged to the centralized drift registry.

## Quality Gates
These skills are integrated into the primary sync pipeline to ensure that no dataset is promoted to the dashboard without a passing Quality Score.
