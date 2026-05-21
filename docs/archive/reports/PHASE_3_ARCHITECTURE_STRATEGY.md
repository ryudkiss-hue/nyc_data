# NYC DOT PHASE 3: Distributed Systems Architecture & Implementation Strategy
**Weeks 13-24 | Orchestration, Distributed Processing, Production Hardening**

---

## EXECUTIVE SUMMARY

**Objective:** Scale PHASE 1-2 capabilities (98 production modules, 500+ tests) to distributed execution with enterprise SLA enforcement, enabling:
- **Weeks 13-16:** Airflow DAG orchestration with SLA monitoring
- **Weeks 17-20:** Spark distributed processing (material costing, geospatial joins at scale)
- **Weeks 21-24:** Production hardening (HA/DR, caching, performance optimization)
- **Post-Implementation:** 24-metric KPI framework and dashboard

**Technology Stack (Azure-Native):**
- **Orchestration:** Apache Airflow 2.5+ on AKS (Azure Kubernetes Service)
- **Distributed Processing:** Databricks on Azure (Spark 3.3+, SQL, ML)
- **Data Storage:** Azure Database for PostgreSQL (read replicas, geo-replication)
- **Caching:** Azure Cache for Redis (distributed query result cache)
- **Observability:** Azure Monitor + Log Analytics + Power BI
- **Messaging:** Azure Service Bus (event-driven orchestration)
- **IaC:** Terraform/Helm for repeatable deployments

**Expected Outcomes:**
- ✅ 10+ Airflow DAGs running 24/7 with <5% SLA violation rate
- ✅ Material costing: 100M records in <5 minutes (Spark)
- ✅ Query cache hit rate >80%, 40% performance improvement
- ✅ RTO <1 hour, RPO <5 minutes (automated DR drills)
- ✅ 24 KPIs tracked daily with anomaly detection

---

## PART 1: ARCHITECTURE OVERVIEW

### 1.1 PHASE 1-2 Integration Points

**Current State (End of PHASE 2):**
```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1-2 ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [Socrata API] → [Schema Registry] → [Lineage Tracking]     │
│       │              │                      │                │
│       v              v                      v                │
│  [Raw Ingestion] → [Quality Validation] → [DAG Dependency]  │
│       │              │                      │                │
│       v              v                      v                │
│  [Entity Resolution] → [CDC/SCD Type 2] → [Temporal]        │
│       │                                     │                │
│       └─────────────────────────────────────┘                │
│                     │                                         │
│                     v                                         │
│         [PostgreSQL + PostGIS] ← [Compliance Check]         │
│                     │                                         │
│       ┌─────────────┼─────────────┐                          │
│       v             v             v                          │
│  [API Layer] [Query Cache] [Analytics Views]                │
│       │             │             │                          │
│       └─────────────┼─────────────┘                          │
│                     v                                         │
│         [Governance + Audit Log]                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key PHASE 1-2 Components to Integrate:**

| Module | Purpose | PHASE 3 Dependency |
|--------|---------|-------------------|
| [`lineage_core.py`](socrata_toolkit/lineage_core.py) | DAG dependency graph | Auto-generate Airflow DAGs |
| [`lineage_persistence.py`](socrata_toolkit/lineage_persistence.py) | Lineage storage | Track DAG execution history |
| [`schema_registry.py`](socrata_toolkit/schema_registry.py) | Schema versioning | Validate Spark outputs |
| [`quality_validator.py`](socrata_toolkit/quality_validator.py) | Data quality | SLA enforcement in DAGs |
| [`material_standards.py`](socrata_toolkit/material_standards.py) | Material compliance | Spark costing validation |
| [`scd_type2.py`](socrata_toolkit/scd_type2.py) | Temporal tracking | Maintain history in Spark |
| [`observability.py`](socrata_toolkit/observability.py) | Metrics/tracing | Power BI dashboards |
| [`api/main.py`](socrata_toolkit/api/main.py) | REST API | Query cache integration |

---

### 1.2 PHASE 3 Distributed Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                 PHASE 3 DISTRIBUTED ARCHITECTURE                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INGESTION TIER (Every 6 hours)                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [Socrata API] → [SocrataIngestion Operator]              │ │
│  │      ↓                                                     │ │
│  │  [Schema Validation] → [Lineage Tracking]                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                       │
│  ORCHESTRATION TIER (Airflow on AKS)                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ DAG: socrata_ingest_6h                              │  │ │
│  │  │  └─→ [Quality Validation] → [SLA Check]            │  │ │
│  │  │                                                      │  │ │
│  │  │ DAG: compliance_check_24h                            │  │ │
│  │  │  └─→ [Material Compliance] → [Alert if Failed]      │  │ │
│  │  │                                                      │  │ │
│  │  │ DAG: spark_lineage_daily                             │  │ │
│  │  │  └─→ [SparkSubmitOperator] → [Costing + Geospatial]│  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  Sensor Patterns:                                          │ │
│  │  • DataFreshnessOperator: Trigger if data >6h old         │ │
│  │  • ExternalTaskSensor: Wait for upstream Socrata update   │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                       │
│  PROCESSING TIER (Spark on Databricks)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Material Lifecycle Costing                           │  │ │
│  │  │ • Input: Raw materials + work orders (100M rows)    │  │ │
│  │  │ • Logic: Cost aggregation by material + location    │  │ │
│  │  │ • Output: Spark DataFrame → PostgreSQL (5 min)      │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Distributed Geospatial Joins                         │  │ │
│  │  │ • Input: Blocks + Segments + Materials (ST_Joins)   │  │ │
│  │  │ • Logic: Partition by geography, parallel execution │  │ │
│  │  │ • Output: Feature table (service areas, hotspots)   │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Incremental Processing (Delta Lake)                 │  │ │
│  │  │ • Only process new/changed records per day          │  │ │
│  │  │ • Full history maintained (SCD Type 2)              │  │ │
│  │  │ • ACID transactions for consistency                 │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                       │
│  STORAGE TIER (PostgreSQL + Redis)                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │  [Azure Database PostgreSQL]                              │ │
│  │  • Primary: 32 vCPU, 128 GB RAM, 1 TB SSD                 │ │
│  │  • Read Replica #1: Analytics queries (BI tools)          │ │
│  │  • Read Replica #2: Spark ephemeral reads                 │ │
│  │  • Geo-replica: DR failover (paired region)               │ │
│  │                                                             │ │
│  │  [Azure Cache for Redis]                                  │ │
│  │  • Query results (1-hour TTL, <1ms latency)              │ │
│  │  • API responses (5-minute TTL, 80%+ hit rate)            │ │
│  │  • Session state (distributed Airflow tasks)              │ │
│  │                                                             │ │
│  │  [PgBouncer Connection Pooling]                           │ │
│  │  • Max connections: 500 → pooled to 100                   │ │
│  │  • 3x improvement in connection throughput                │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                       │
│  SERVING TIER (API + Observability)                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Flask API (from PHASE 2)                             │  │ │
│  │  │ • Rate limiting: 1000 req/min per client             │  │ │
│  │  │ • Response caching: 5 min (Redis)                    │  │ │
│  │  │ • Version support: /v1, /v2 endpoints                │  │ │
│  │  │ • Auth: Azure AD + RBAC (groups → scopes)            │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Power BI + Dashboards (Office 365 integration)      │  │ │
│  │  │ • KPI dashboards: Updated hourly                    │  │ │
│  │  │ • Alerting: Teams notifications                     │  │ │
│  │  │ • Embedded in SharePoint                            │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Azure Monitor + Log Analytics                        │  │ │
│  │  │ • Real-time alerts: SLA breaches, Spark failures    │  │ │
│  │  │ • Trace DAG execution → System behavior             │  │ │
│  │  │ • Cost tracking: Per-job billing analysis           │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## PART 2: DETAILED PHASE 3 DESIGN

### 2.1 WEEKS 13-16: Airflow DAG Orchestration & SLA Monitoring

#### 2.1.1 Airflow Deployment Strategy

**Target State:**
- **Airflow Version:** 2.5.3 (LTS)
- **Executor:** Kubernetes Pod Operator on AKS
- **Database:** Azure Database for PostgreSQL (15.0+)
- **Metadata Storage:** Persistent Azure Blob Storage
- **High Availability:** 3-node Airflow scheduler cluster

**Kubernetes Deployment (AKS):**
```yaml
# Structure (Helm Charts)
airflow/
├── values.yaml                          # Configuration overrides
├── values-dev.yaml
├── values-prod.yaml
└── kubernetes/
    ├── scheduler-deployment.yaml        # 3 replicas, affinity rules
    ├── webui-deployment.yaml            # 2 replicas, load-balanced
    ├── pvc-airflow-logs.yaml            # Persistent volume for logs
    ├── configmap-airflow-config.yaml    # Airflow configuration
    └── network-policy.yaml              # Restrict pod-to-pod traffic
```

**Core Configuration:**
```ini
# airflow.cfg equivalents
[core]
executor = KubernetesExecutor
parallelism = 32                    # Max concurrent DAGs
max_active_tasks_per_dag = 16       # Per-DAG concurrency
load_examples = False               # Production: no examples
dags_folder = /opt/airflow/dags     # DAG registry location

[scheduler]
max_dagruns_of_each_dag_length = 10 # Keep 10 runs per DAG
catchup_by_default = False          # Don't backfill by default
dag_dir_list_interval = 30          # Scan DAGs every 30s

[logging]
remote_logging = True               # Stream to Azure Blob
remote_log_conn_id = azure_blob     # Airflow connection

[webserver]
expose_config = False               # Security: hide config
authenticate = True                 # Require login
auth_backend = airflow.contrib.auth.backends.azure_ad
```

#### 2.1.2 DAG Registry & Auto-Discovery

**Problem:** Manual DAG creation is error-prone and doesn't leverage existing lineage data.

**Solution:** Auto-generate Airflow DAGs from [`lineage_core.py`](socrata_toolkit/lineage_core.py) DAG definitions.

**DAG Generation Pipeline:**

```python
# airflow/dags/dag_generator.py (NEW)
"""Dynamically generate Airflow DAGs from Socrata Toolkit lineage."""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.databricks.operators.databricks_sql import DatabricksSqlOperator
from socrata_toolkit.lineage_core import DAG as LineageDAG
from socrata_toolkit.lineage_persistence import load_lineage_from_db
from datetime import datetime, timedelta

def generate_dags():
    """Load lineage definitions and create Airflow DAGs."""
    
    # Load PHASE 1-2 lineage from PostgreSQL
    lineage = load_lineage_from_db(schema='lineage')
    
    for node in lineage.get_all_nodes():
        dag_id = f"dag_{node.name.lower().replace(' ', '_')}"
        
        # Create Airflow DAG
        dag = DAG(
            dag_id=dag_id,
            default_args={
                'owner': node.owner,
                'depends_on_past': False,
                'retries': 2,
                'retry_delay': timedelta(minutes=5),
                'start_date': datetime(2026, 6, 1),
            },
            schedule_interval=node.schedule or '@once',
            description=node.description,
            catchup=False,
            tags=['phase3', node.node_type.value]
        )
        
        # Add tasks for each transformation
        prev_task = None
        for edge in node.get_outgoing_edges():
            task = create_task_from_node(
                dag=dag,
                node=edge.target,
                lineage=lineage
            )
            if prev_task:
                task.set_upstream(prev_task)
            prev_task = task
        
        # Register DAG globally
        globals()[dag_id] = dag

# This approach ensures:
# ✓ Single source of truth (lineage definitions)
# ✓ Automatic task dependency resolution
# ✓ Consistent error handling and retry logic
# ✓ Audit trail (who/what modified the DAG)
```

**DAG Templates (10+ planned):**

| DAG | Frequency | Owner | Key Tasks |
|-----|-----------|-------|-----------|
| `socrata_ingest_6h` | Every 6h | Data Eng | Fetch Socrata → Validate Schema → Record Lineage |
| `compliance_check_24h` | Daily 2am | Compliance | Material Standards → ADA Check → Alert if failed |
| `quality_validation_6h` | Every 6h | Quality | Run expectations → Compute metrics → SLA check |
| `spark_costing_daily` | Daily 1am | Analytics | Material lifecycle costing (100M rows) |
| `spark_geospatial_daily` | Daily 2am | Analytics | Distributed geospatial joins + hotspot detection |
| `lineage_impact_24h` | Daily 6am | Governance | Impact analysis for schema changes |
| `api_cache_refresh_1h` | Every 1h | Ops | Refresh Redis cache for popular queries |
| `entity_dedup_weekly` | Sunday 11pm | Data Eng | Entity resolution and merge logic |
| `scd_type2_sync_6h` | Every 6h | Analytics | Maintain temporal dimension (SCD Type 2) |
| `kpi_materialization_1h` | Every 1h | Analytics | Compute 24 KPIs (costing, ADA, efficiency) |
| `backup_snapshot_24h` | Daily 3am | Ops | PostgreSQL WAL archival + transaction log |
| `dr_failover_test_monthly` | 1st of month | Ops | Test RTO/RPO procedures |

#### 2.1.3 SLA Monitoring & Alerting

**SLA Definitions (PostgreSQL):**

```sql
-- Table: lineage.dag_slas (NEW)
CREATE TABLE lineage.dag_slas (
    sla_id UUID PRIMARY KEY,
    dag_id VARCHAR(255) NOT NULL,
    sla_type VARCHAR(50),              -- 'execution_time', 'data_freshness'
    threshold INTERVAL,                -- e.g., '30 minutes'
    severity VARCHAR(20),              -- 'critical', 'warning'
    alert_on_breach BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (dag_id) REFERENCES lineage.dags(dag_id)
);

-- Example SLAs
INSERT INTO lineage.dag_slas (dag_id, sla_type, threshold, severity) VALUES
    ('socrata_ingest_6h', 'execution_time', '45 minutes', 'critical'),
    ('socrata_ingest_6h', 'data_freshness', '6 hours', 'warning'),
    ('compliance_check_24h', 'execution_time', '2 hours', 'critical'),
    ('spark_costing_daily', 'execution_time', '10 minutes', 'warning'),
    ('spark_geospatial_daily', 'execution_time', '15 minutes', 'warning');
```

**Airflow Integration:**

```python
# airflow/plugins/sla_monitors.py (NEW)
"""SLA monitoring and alerting for DAGs."""

from airflow.models import DagRun
from airflow.exceptions import AirflowSLAMissedException
from socrata_toolkit.observability_sla import SLATracker
from socrata_toolkit.alert_delivery import send_alert
import logging

logger = logging.getLogger(__name__)

def monitor_dag_sla(context):
    """Check DAG execution time against SLA thresholds."""
    dag_run = context['dag_run']
    sla_tracker = SLATracker()
    
    # Load SLA thresholds from DB
    slas = sla_tracker.get_slas_for_dag(dag_run.dag_id)
    
    for sla in slas:
        if sla.sla_type == 'execution_time':
            execution_duration = dag_run.duration
            if execution_duration > sla.threshold:
                send_alert(
                    channel='teams',
                    title=f'⚠️ SLA Breach: {dag_run.dag_id}',
                    message=f'Execution took {execution_duration.total_seconds()}s, threshold {sla.threshold.total_seconds()}s',
                    severity=sla.severity
                )
                sla_tracker.record_breach(
                    dag_id=dag_run.dag_id,
                    sla_id=sla.sla_id,
                    actual_duration=execution_duration,
                    threshold=sla.threshold
                )

# Each DAG gets an on_failure_callback for SLA monitoring
default_args = {
    'on_failure_callback': [monitor_dag_sla],
    'sla': timedelta(minutes=45),  # Airflow native SLA
}
```

---

### 2.2 WEEKS 17-20: Spark Distributed Processing

#### 2.2.1 Spark Cluster Architecture (Databricks)

**Deployment on Azure Databricks:**

```yaml
# databricks/cluster_config.json
{
  "cluster_name": "nyc_dot_production",
  "spark_version": "13.3.x-scala2.12",           # Latest stable
  "node_type_id": "Standard_D32s_v3",            # 32 vCPU, 128 GB RAM
  "driver_node_type_id": "Standard_D16s_v3",     # Driver node
  "num_workers": 16,                              # 16 workers = 512 vCPU
  "autoscale": {
    "min_workers": 4,
    "max_workers": 32
  },
  "aws_attributes": {
    "availability": "SPOT",                      # Cost: 70% less
    "zone_id": "az1"
  },
  "init_scripts": [
    "dbfs:/scripts/install_postgis_driver.sh"    # PostGIS connector
  ],
  "spark_conf": {
    "spark.sql.adaptive.enabled": "true",        # Query optimization
    "spark.sql.adaptive.skewJoin.enabled": "true",
    "spark.databricks.io.cache.enabled": "true", # IO cache
    "spark.databricks.delta.preview.enabled": "true",
    "spark.sql.shuffle.partitions": "256"        # Tuned for data volume
  },
  "enable_elastic_disk": true,
  "disk_spec": {
    "disk_count": 8,
    "disk_size": 256                             # 2 TB total
  }
}
```

**Cost Profile:**
- **Dev/Test Cluster:** 4 workers × $0.25/hr = $1/hr (~$240/month)
- **Production Cluster:** 16 workers × $0.25/hr = $4/hr (~$2,880/month, amortized)
- **Monthly Databricks Workspace:** $1,000 (unit consumption)
- **Total:** ~$4,000/month (production)

#### 2.2.2 Spark Applications (PySpark)

**Job 1: Material Lifecycle Costing (Distributed)**

```python
# spark_jobs/material_costing.py (NEW)
"""
Distributed material lifecycle costing across 100M+ work orders.

Replaces single-machine query from PHASE 2.
Expected runtime: <5 minutes for full dataset.
"""

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import *
import logging

logger = logging.getLogger(__name__)

def run_material_costing():
    """Execute distributed material costing pipeline."""
    
    spark = SparkSession.builder \
        .appName("material_costing_daily") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    # STEP 1: Load source data (incremental, partitioned)
    # Only process records updated in last 24h (SCD Type 2 logic)
    work_orders = spark.read.format("jdbc") \
        .option("url", "jdbc:postgresql://...") \
        .option("dbtable", "(SELECT * FROM work_orders WHERE updated_at > now() - interval '24 hours') AS t") \
        .option("user", "spark_user") \
        .option("password", spark.conf.get("spark.databricks.secrets.password")) \
        .load() \
        .repartition(256, "borough_id", "updated_date")  # Partition by geography
    
    materials = spark.read.format("jdbc") \
        .option("url", "jdbc:postgresql://...") \
        .option("dbtable", "materials") \
        .load() \
        .broadcast()  # Small lookup table
    
    # STEP 2: Join and calculate costs
    costs = work_orders \
        .join(materials, on="material_id", how="inner") \
        .select(
            "work_order_id",
            "material_id",
            "quantity",
            "unit_cost",
            (F.col("quantity") * F.col("unit_cost")).alias("total_cost"),
            "borough_id",
            "block_id",
            "segment_id",
            "updated_at"
        )
    
    # STEP 3: Aggregate by material + geography
    material_summary = costs \
        .groupBy("borough_id", "block_id", "segment_id", "material_id") \
        .agg(
            F.sum("total_cost").alias("total_cost"),
            F.count("work_order_id").alias("work_order_count"),
            F.avg("unit_cost").alias("avg_unit_cost"),
            F.max("updated_at").alias("last_updated")
        ) \
        .cache()
    
    # STEP 4: Write to PostgreSQL (upsert with CDC)
    material_summary.write \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://...") \
        .option("dbtable", "analytics.material_costs_summary") \
        .option("user", "spark_user") \
        .option("mode", "append")  # Spark doesn't support upsert; use MERGE in PostgreSQL
        .save()
    
    # STEP 5: Log execution metrics
    logger.info(f"Material costing completed: {material_summary.count()} rows in {spark.sparkContext.status().executorDeadline}")
    
    # STEP 6: Record lineage (integration with PHASE 1-2)
    from socrata_toolkit.lineage_persistence import record_execution
    record_execution(
        node_id='spark_costing_daily',
        rows_processed=work_orders.count(),
        rows_output=material_summary.count(),
        execution_time=spark.sparkContext.status().executorDeadline,
        status='success'
    )
    
    spark.stop()

if __name__ == '__main__':
    run_material_costing()
```

**Job 2: Distributed Geospatial Joins**

```python
# spark_jobs/geospatial_joins.py (NEW)
"""
Distributed geospatial operations: blocks × segments × materials.
Uses Delta Lake for ACID transactions and incremental processing.
"""

from pyspark.sql import SparkSession, functions as F
from sedona.spark import *
import logging

logger = logging.getLogger(__name__)

def run_geospatial_analysis():
    """Execute distributed geospatial joins."""
    
    spark = SparkSession.builder \
        .appName("geospatial_daily") \
        .config("spark.jars.packages", "org.apache.sedona:sedona-spark-3.3_2.12:1.4.1") \
        .getOrCreate()
    
    # Initialize Sedona (Spark-native geospatial)
    SedonaContext.create(spark)
    
    # STEP 1: Load NYC geometry data (precomputed, cached)
    blocks = spark.read.format("delta").load("dbfs:/delta/blocks") \
        .select("block_id", "geometry")
    
    segments = spark.read.format("delta").load("dbfs:/delta/segments") \
        .select("segment_id", "geometry", "material_id")
    
    # STEP 2: Spatial join (blocks ST_INTERSECTS segments)
    block_segment_join = ST_Join(
        block_geom=blocks,
        segment_geom=segments,
        condition="ST_Intersects(block_geom, segment_geom)",
        return_multiple=True
    )
    
    # STEP 3: Aggregate by material + location
    spatial_summary = block_segment_join \
        .groupBy("block_id", "segment_id", "material_id") \
        .agg(
            F.sum(F.st_area("geometry")).alias("total_area_sq_ft"),
            F.count("*").alias("geometry_count")
        )
    
    # STEP 4: Write to Delta Lake (ACID, versioning)
    spatial_summary.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/delta/geospatial_summary")
    
    # STEP 5: Mirror to PostgreSQL for API serving
    spatial_summary.write \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://...") \
        .option("dbtable", "analytics.geospatial_summary") \
        .save()
    
    logger.info(f"Geospatial joins completed: {spatial_summary.count()} features")
    
    spark.stop()

if __name__ == '__main__':
    run_geospatial_analysis()
```

#### 2.2.3 Spark Job Integration with Airflow

**Airflow Operator for Spark Submission:**

```python
# airflow/dags/spark_orchestration.py (NEW)
"""DAGs that trigger Databricks Spark jobs."""

from airflow import DAG
from airflow.providers.databricks.operators.databricks_sql import DatabricksSqlOperator
from airflow.providers.databricks.operators.databricks_sql import DatabricksSubmitRunOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'analytics_team',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='spark_costing_daily',
    default_args=default_args,
    schedule_interval='0 1 * * *',  # 1 AM daily
    catchup=False,
    tags=['phase3', 'spark']
) as dag:
    
    # Task 1: Run Spark job
    run_costing = DatabricksSubmitRunOperator(
        task_id='submit_material_costing',
        databricks_conn_id='databricks_prod',
        new_cluster={
            "spark_version": "13.3.x-scala2.12",
            "node_type_id": "Standard_D16s_v3",
            "num_workers": 4,
            "aws_attributes": {"availability": "SPOT"}
        },
        spark_python_task={
            "python_file": "dbfs:/Workspace/spark_jobs/material_costing.py"
        },
        timeout_seconds=600  # 10 minutes max
    )
    
    # Task 2: Validate output (compare Spark vs PostgreSQL)
    validate_results = DatabricksSqlOperator(
        task_id='validate_spark_output',
        databricks_conn_id='databricks_prod',
        sql="""
        SELECT
            COUNT(*) as spark_rows,
            SUM(total_cost) as spark_total_cost
        FROM analytics.material_costs_summary
        WHERE last_updated >= CURRENT_DATE - INTERVAL '1 day'
        """
    )
    
    # Task 3: Check SLA (execution time <5 min)
    # Airflow will automatically fail if task took >5 min
    
    run_costing >> validate_results
```

---

### 2.3 WEEKS 21-24: Production Hardening & Performance Optimization

#### 2.3.1 Caching Layer (Azure Cache for Redis)

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Redis Caching Tiers                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Tier 1: Query Result Cache (1-hour TTL)                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Key: hash(query_sql + params)                           │ │
│ │ Value: {rows: [...], schema: {...}, cached_at: ts}      │ │
│ │ TTL: 1 hour (configurable per query type)               │ │
│ │ Size: 50 GB (fits top 10K queries)                      │ │
│ │ Hit Rate Target: >80%                                    │ │
│ │                                                           │ │
│ │ Example:                                                  │ │
│ │   GET cache:query:{hash}                                 │ │
│ │   SET cache:query:{hash} {result_json} EX 3600          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Tier 2: API Response Cache (5-minute TTL)                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Key: /api/v1/materials/{borough_id} → GET params        │ │
│ │ Value: {response_body, status_code, headers}            │ │
│ │ TTL: 5 minutes (dashboard refresh cycle)                │ │
│ │ Size: 10 GB (cache popular endpoints)                    │ │
│ │ Hit Rate Target: >70%                                    │ │
│ │                                                           │ │
│ │ Example:                                                  │ │
│ │   GET cache:api:/v1/materials/1                         │ │
│ │   SET cache:api:/v1/materials/1 {json} EX 300           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Tier 3: Session State (distributed Airflow)                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Key: airflow:dag_run:{dag_id}:{run_id}                  │ │
│ │ Value: {state, start_time, end_time, status}            │ │
│ │ TTL: 7 days (keep run history)                           │ │
│ │ Size: 5 GB (10K concurrent DAG runs)                     │ │
│ │                                                           │
│ │ Example:                                                  │
│ │   SET airflow:dag_run:socrata_ingest:2026-06-10 {...} EX 604800
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Redis Configuration (Azure):**

```json
{
  "redis_tier": "premium",                    // Enterprise features
  "capacity": 13,                             // 550 GB (P5)
  "family": "P",                              // Premium
  "enable_non_ssl_port": false,               // TLS only
  "minimum_tls_version": "1.2",
  "zones": ["1", "2"],                        // Zone redundancy (HA)
  "enable_data_persistence": true,            // RDB snapshots
  "rdb_backup_frequency": "every_6_hours",    // Daily backups
  "notify_keyspace_events": "AKE",            // Event notifications
  "enable_module": ["RedisBloom"]             // Bloom filters for dedup
}
```

**Caching Implementation (Python):**

```python
# socrata_toolkit/api/cache.py (UPDATED for PHASE 3)
"""Redis caching for query results and API responses."""

import redis
import json
import hashlib
from functools import wraps
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Manage multi-tier caching with Redis."""
    
    def __init__(self, redis_host: str, redis_port: int = 6380, ssl=True):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            ssl=ssl,
            decode_responses=True
        )
        self.hit_count = 0
        self.miss_count = 0
    
    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        params_json = json.dumps(kwargs, sort_keys=True)
        params_hash = hashlib.md5(params_json.encode()).hexdigest()
        return f"{prefix}:{params_hash}"
    
    def cache_query_result(self, ttl: int = 3600):
        """Decorator to cache SQL query results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from query + params
                cache_key = self.get_cache_key("query", *args, **kwargs)
                
                # Check cache
                cached = self.redis.get(cache_key)
                if cached:
                    self.hit_count += 1
                    logger.info(f"Cache hit: {cache_key}")
                    return json.loads(cached)
                
                # Cache miss: execute query
                self.miss_count += 1
                result = func(*args, **kwargs)
                
                # Store in Redis with TTL
                self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, default=str)
                )
                logger.info(f"Cache miss: {cache_key} (TTL {ttl}s)")
                
                return result
            
            return wrapper
        return decorator
    
    def cache_api_response(self, ttl: int = 300):
        """Decorator to cache API responses."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Cache key from endpoint + params
                endpoint = args[0].__name__ if args else kwargs.get('endpoint')
                cache_key = self.get_cache_key("api", endpoint=endpoint, **kwargs)
                
                cached = self.redis.get(cache_key)
                if cached:
                    self.hit_count += 1
                    return json.loads(cached)
                
                response = func(*args, **kwargs)
                self.redis.setex(cache_key, ttl, json.dumps(response, default=str))
                self.miss_count += 1
                
                return response
            
            return wrapper
        return decorator
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate (%)."""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total * 100) if total > 0 else 0.0
    
    def clear_cache_by_pattern(self, pattern: str):
        """Clear cache entries matching pattern (e.g., 'query:*')."""
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries: {pattern}")

# Usage in API:
cache_manager = CacheManager(
    redis_host='nyc-dot-cache.redis.cache.windows.net',
    redis_port=6380,
    ssl=True
)

@cache_manager.cache_query_result(ttl=3600)
def get_material_costs_by_borough(borough_id: int):
    """Get material costs (cached for 1 hour)."""
    # This will be cached
    return db.query("SELECT * FROM material_costs WHERE borough_id = ?", borough_id)

@cache_manager.cache_api_response(ttl=300)
def api_get_kpi_dashboard():
    """Get KPI dashboard (cached for 5 minutes)."""
    return fetch_kpi_metrics()
```

#### 2.3.2 Connection Pooling (PgBouncer)

**Problem:** PostgreSQL has a hard limit of ~200 connections; Airflow DAGs × Spark workers can exceed this.

**Solution:** Deploy PgBouncer as reverse proxy.

**PgBouncer Configuration:**

```ini
# pgbouncer.ini
[databases]
nyc_dot = host=nyc-dot-postgres.postgres.database.azure.com port=5432 dbname=nyc_dot

[pgbouncer]
# Connection pooling parameters
pool_mode = transaction              # Connection pooling at transaction level
max_client_conn = 500                # Accept up to 500 client connections
default_pool_size = 25               # Maintain 25 connections per database
min_pool_size = 10                   # Minimum 10 connections
reserve_pool_size = 5                # Reserve 5 for emergencies
reserve_pool_timeout = 30            # Timeout before using reserves
max_db_connections = 100             # Max 100 actual DB connections
max_user_connections = 100           # Max per user
server_idle_timeout = 600            # Idle timeout (10 min)

# Performance tuning
query_wait_timeout = 120             # Wait 2 min for available connection
auto_db_idle_in_transaction_session_timeout = 30

# Monitoring
stats_period = 60                    # Report stats every 60s
log_connections = 1
log_disconnections = 1
```

**Deployment (Kubernetes):**

```yaml
# kubernetes/pgbouncer-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: data-platform
spec:
  replicas: 3                         # HA with 3 replicas
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer:1.17
        ports:
        - containerPort: 6432
        env:
        - name: PGBOUNCER_HOST
          value: "0.0.0.0"
        - name: PGBOUNCER_PORT
          value: "6432"
        livenessProbe:
          tcpSocket:
            port: 6432
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          tcpSocket:
            port: 6432
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: pgbouncer
  namespace: data-platform
spec:
  selector:
    app: pgbouncer
  ports:
  - port: 6432
    targetPort: 6432
  type: ClusterIP
```

**Impact:**
- 500 client connections → pooled to 100 actual DB connections (5x reduction)
- 3x faster connection establishment
- Reduced memory pressure on PostgreSQL

#### 2.3.3 PostgreSQL Read Replicas & Geo-Replication

**Primary Setup (Azure Database for PostgreSQL):**

```sql
-- Primary server (Azure)
-- Configuration:
-- Compute: D32s v3 (32 vCPU, 128 GB RAM)
-- Storage: 1 TB SSD
-- Backup: Automated daily, 35-day retention
-- Monitoring: Azure Monitor integration

-- Create replication user
CREATE ROLE replicator WITH REPLICATION CREATEDB LOGIN ENCRYPTED PASSWORD 'xxxx';
GRANT CONNECT ON DATABASE nyc_dot TO replicator;

-- Enable logical replication (for PHASE 4 CDC)
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET max_logical_replication_workers = 4;
SELECT pg_ctl_reload();
```

**Read Replicas (Azure):**

```
Primary Server (nyc-dot-postgres.postgres.database.azure.com)
  │
  ├─→ Read Replica #1 (read-1.postgres.database.azure.com) [Analytics Queries]
  │   └─ D32s v3, 1 TB, same region
  │
  └─→ Read Replica #2 (read-2.postgres.database.azure.com) [Spark Ephemeral]
      └─ D32s v3, 1 TB, same region

Geo-Replica (Disaster Recovery)
  └─→ Secondary Region (East US 2)
      └─ D32s v3, 1 TB, ready for failover
```

**Connection Routing (Azure)::**

```python
# Database connection routing based on query type
# socrata_toolkit/persistence.py (UPDATED)

class DatabaseRouter:
    """Route connections to primary or replicas."""
    
    WRITE_OPERATIONS = {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}
    
    def __init__(self):
        self.primary_dsn = os.getenv('PG_PRIMARY_DSN')
        self.read_replica_1_dsn = os.getenv('PG_READ_1_DSN')
        self.read_replica_2_dsn = os.getenv('PG_READ_2_DSN')
    
    def get_connection(self, query: str, is_write: bool = False):
        """Select connection based on query type."""
        
        # Write queries always go to primary
        if is_write or any(op in query.upper() for op in self.WRITE_OPERATIONS):
            return psycopg2.connect(self.primary_dsn)
        
        # Read queries round-robin between replicas
        import random
        replica = random.choice([self.read_replica_1_dsn, self.read_replica_2_dsn])
        return psycopg2.connect(replica)

# Usage
router = DatabaseRouter()

# Write: goes to primary
with router.get_connection("INSERT INTO materials (...)", is_write=True) as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO materials ...")

# Read: goes to replica
with router.get_connection("SELECT * FROM materials WHERE ...") as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
```

#### 2.3.4 High Availability & Disaster Recovery

**RTO <1 Hour, RPO <5 Minutes:**

```
┌──────────────────────────────────────────────────────────────────┐
│               HA/DR Architecture (Azure Native)                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│ PRIMARY REGION (East US)                                          │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │                                                             │   │
│ │ PostgreSQL Primary Server (nyc-dot-postgres)              │   │
│ │  ├─ Compute: D32s v3 (32 vCPU, 128 GB)                    │   │
│ │  ├─ Storage: 1 TB SSD                                      │   │
│ │  └─ WAL Archival: Every 5 minutes to Azure Blob Storage   │   │
│ │                                                             │   │
│ │ Read Replicas (in same region)                             │   │
│ │  ├─ Replica #1: Analytics queries                          │   │
│ │  └─ Replica #2: Spark reads                                │   │
│ │                                                             │   │
│ │ Automated Backups:                                         │   │
│ │  ├─ Daily snapshots (35-day retention)                     │   │
│ │  ├─ Transaction logs (7-day retention)                     │   │
│ │  └─ Point-in-time recovery (PITR)                          │   │
│ │                                                             │   │
│ │ Failover Trigger:                                          │   │
│ │  └─ Azure Monitor alert if primary unavailable >5 min     │   │
│ │                                                             │   │
│ └────────────────────────────────────────────────────────────┘   │
│         ↑ Primary Data Replication (synchronous) ↓                │
│         ↓ WAL Archival (asynchronous, 5 min lag) ↑                │
│ SECONDARY REGION (East US 2)                                      │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │                                                             │   │
│ │ Geo-Replica (standby, read-only)                           │   │
│ │  ├─ Compute: D32s v3 (32 vCPU, 128 GB) [WARM]             │   │
│ │  ├─ Storage: 1 TB SSD                                      │   │
│ │  └─ Replication lag: <1 minute                             │   │
│ │                                                             │   │
│ │ Automated Failover Process:                                │   │
│ │  1. Monitor detects primary failure (5 min timeout)        │   │
│ │  2. Promote geo-replica to primary (30 sec)                │   │
│ │  3. Update DNS/connection strings (1 min)                  │   │
│ │  4. Resume writes on new primary (1 min)                   │   │
│ │  5. Total RTO: ~37 minutes (< 1 hour ✓)                    │   │
│ │                                                             │   │
│ │ Recovery Options (if needed):                              │   │
│ │  a) Point-in-time restore: <5 min RPO ✓                   │   │
│ │  b) Last transaction log: <1 min RPO ✓                    │   │
│ │                                                             │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Backup Strategy:**

```sql
-- WAL Archival Configuration (in Azure PostgreSQL)
-- Automatically archives transaction logs every 5 minutes

-- Monitor archival progress
SELECT
    wal_last_received_lsn,
    wal_last_applied_lsn,
    replay_lag,
    write_lag
FROM pg_stat_replication;

-- Point-in-time recovery example (if needed)
-- 1. Create new server from backup
-- 2. Restore to specific timestamp
-- 3. Verify data integrity
-- 4. Switch traffic (via connection string)
```

**Automated DR Drills (Monthly):**

```python
# airflow/dags/dr_failover_test.py (NEW)
"""Monthly DR drill to verify RTO/RPO."""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def test_failover():
    """Simulate failover to geo-replica and measure RTO."""
    
    import psycopg2
    import time
    
    # Step 1: Record baseline metrics
    primary = psycopg2.connect("dbname=nyc_dot host=nyc-dot-postgres.postgres.database.azure.com")
    baseline_count = primary.cursor().execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
    baseline_time = datetime.utcnow()
    
    # Step 2: Initiate failover (Azure API call)
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient
    
    credential = DefaultAzureCredential()
    client = PostgreSQLManagementClient(credential, subscription_id='xxx')
    
    # Promote geo-replica (actual failover)
    client.servers.begin_promote_read_replica(
        resource_group_name='nyc-dot-rg',
        server_name='nyc-dot-postgres-secondary'
    )
    
    failover_start = time.time()
    
    # Step 3: Monitor and measure RTO
    max_retries = 12  # 60 seconds (5s per retry)
    for i in range(max_retries):
        try:
            # Try to connect to promoted replica
            new_primary = psycopg2.connect(
                "dbname=nyc_dot host=nyc-dot-postgres-secondary.postgres.database.azure.com"
            )
            new_count = new_primary.cursor().execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
            
            rto_seconds = time.time() - failover_start
            
            # Verify data integrity
            if new_count >= baseline_count:
                logger.info(f"✓ Failover successful. RTO: {rto_seconds:.1f}s, Data integrity: OK")
                return {'rto': rto_seconds, 'data_integrity': 'OK'}
            
        except psycopg2.OperationalError:
            time.sleep(5)
            continue
    
    raise AirflowException(f"Failover did not complete within {max_retries * 5}s")

def restore_primary():
    """Restore primary server and test failback."""
    # This is a manual step; documented in runbooks
    logger.info("Restore primary server manually from DR backup")
    logger.info("Promote new replica from promoted server")

with DAG(
    dag_id='dr_failover_test',
    default_args={'owner': 'ops'},
    schedule_interval='0 2 1 * *',  # 2 AM on 1st of month
    start_date=datetime(2026, 6, 1)
) as dag:
    
    test = PythonOperator(task_id='test_failover', python_callable=test_failover)
    restore = PythonOperator(task_id='restore_primary', python_callable=restore_primary)
    
    test >> restore
```

---

## PART 3: INTEGRATION STRATEGY

### 3.1 PHASE 1-2 → PHASE 3 Data Flow

```
PHASE 1 Outputs              PHASE 3 Processing                 PHASE 3 Outputs
─────────────────────────────────────────────────────────────────────────────────

[Socrata API]
    ↓
[PHASE 1: Schema Registry]   ──→  [Lineage Auto-Discovery]  ──→  [Airflow DAG Registry]
    ↓                               (lineage_core.py)              (auto-generated DAGs)
[Schema Validated]
    ↓
[PHASE 1: Lineage Tracking]  ──→  [DAG Dependency Graph]     ──→  [Task Dependencies]
    ↓                               (lineage_persistence.py)      (Airflow edges)
[DAG Dependency Graph]
    ↓
[PHASE 2: Quality Validator] ──→  [SLA Enforcement]          ──→  [SLA Breach Alerts]
    ↓                               (quality_sla.py)              (Teams/Slack)
[Quality SLA Checked]
    ↓
[PHASE 2: Entity Resolution] ──→  [Spark Deduplication]      ──→  [Deduplicated Dataset]
    ↓                               (PySpark job)                 (Delta Lake)
[Deduplication Done]
    ↓
[PHASE 2: CDC/SCD Type 2]   ──→  [Temporal Sync]            ──→  [History Maintained]
    ↓                               (SCD Type 2 Spark)           (PostgreSQL versions)
[Temporal History Tracked]
    ↓
[PostGIS Integration]       ──→  [Distributed Geospatial]    ──→  [Spatial Features]
    ↓                               (Spark + Sedona)             (ST_Joins output)
[Spatial Features Ready]
    ↓
[Material Standards]        ──→  [Material Costing at Scale]  ──→  [Cost Summary Table]
    ↓                               (Spark SQL)                   (100M rows → 5 min)
[Material Costing Ready]
    ↓
[Redis Cache Layer]         ──→  [Query Caching]             ──→  [80%+ Hit Rate]
    ↓                               (Azure Cache for Redis)       (<1ms latency)
[Cached Results]
    ↓
[PHASE 2: API Auth]         ──→  [Rate Limiting + Auth]      ──→  [Authorized API Calls]
    ↓                               (Azure AD integration)        (scoped tokens)
[API Response Cached]
    ↓
[Power BI Dashboards]       ──→  [KPI Materialization]       ──→  [24 Metrics Tracked]
    ↓                               (Spark jobs, hourly)          (Real-time dashboard)
[Live Metrics Visible]
```

### 3.2 Configuration Management

**Environment-Specific Configs:**

```yaml
# config/airflow/values-dev.yaml
airflow:
  webui:
    replicas: 1
  scheduler:
    replicas: 1
  workers:
    replicas: 2
  database:
    host: "airflow-postgres-dev.postgres.database.azure.com"
    poolSize: 10
  redis:
    host: "airflow-redis-dev.redis.cache.windows.net"
  dags:
    schedule_interval: "@once"          # Dev: manual only

# config/airflow/values-prod.yaml
airflow:
  webui:
    replicas: 3
  scheduler:
    replicas: 3                         # HA scheduling
  workers:
    replicas: 10
  database:
    host: "airflow-postgres.postgres.database.azure.com"
    poolSize: 50
    read_replicas:
      - "airflow-read-1.postgres.database.azure.com"
      - "airflow-read-2.postgres.database.azure.com"
  redis:
    host: "airflow-redis.redis.cache.windows.net"
  dags:
    schedule_interval: defined per DAG  # Prod: follow schedule

# config/spark/cluster_config-prod.json
{
  "cluster_name": "nyc_dot_production",
  "num_workers": 16,
  "spark_conf": {
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.shuffle.partitions": "256"
  }
}
```

---

## PART 4: IMPLEMENTATION ROADMAP

### 4.1 Timeline & Dependencies

```
W13  W14  W15  W16  W17  W18  W19  W20  W21  W22  W23  W24
──────────────────────────────────────────────────────────

[Airflow Setup + DAG Migration] (Weeks 13-16)
├─ W13: Infrastructure setup (AKS, PostgreSQL, Redis)
├─ W14: Airflow deployment + configuration
├─ W15: DAG auto-generation from lineage
├─ W16: SLA monitoring + alerting
│
└─→ [Spark Development in Sandbox] (Parallel, W14-16)
    ├─ Costing application
    └─ Geospatial joins

     [Spark Deployment & Integration] (Weeks 17-20)
     ├─ W17: Databricks cluster setup
     ├─ W18: Spark jobs migration from PHASE 2
     ├─ W19: Integration with Airflow DAGs
     ├─ W20: Performance validation + benchmarking
     │
     └─→ [Production Hardening Begins] (Parallel, W19-20)
         ├─ Connection pooling (PgBouncer)
         ├─ Read replica setup

          [Production Hardening & HA/DR] (Weeks 21-24)
          ├─ W21: Redis caching layer
          ├─ W22: PostgreSQL geo-replication + failover
          ├─ W23: Automated DR drills + runbooks
          ├─ W24: Performance tuning + optimization
          │
          └─→ [Post-Implementation: KPI Framework] (Parallel, W20-24)
              ├─ KPI definition & computation
              ├─ Dashboard creation (Power BI)
              ├─ Daily reporting setup
              └─ Success metric tracking

Dependencies:
• Airflow setup (W13-14) must complete before DAG migration (W15)
• DAG migration (W15) must complete before SLA integration (W16)
• Spark jobs must be functional (W18) before Airflow integration (W19)
• Connection pooling (W21) and replica setup (W22) can run in parallel
• All infrastructure components must be ready before production hardening (W21)
```

### 4.2 Detailed Weekly Breakdown

#### WEEKS 13-14: Airflow Infrastructure & Setup

| Day | Task | Owner | Deliverable |
|-----|------|-------|------------|
| W13-D1 | Provision AKS cluster (3 nodes, D8s_v3) | DevOps | Kubernetes cluster ready |
| W13-D2 | Deploy PostgreSQL primary + replicas | DBA | Database connections tested |
| W13-D3 | Deploy Redis cache | DevOps | Redis accessible from Airflow |
| W13-D4 | Create Airflow namespaces + RBAC | DevOps | Kubernetes RBAC configured |
| W13-D5 | Deploy Airflow with Helm | Platform Eng | Airflow webUI accessible |
| W14-D1 | Configure Airflow connections (PostgreSQL, Databricks, Redis) | Platform Eng | Connections tested |
| W14-D2 | Set up Airflow variables (environment, secrets) | Platform Eng | Environment-specific configs loaded |
| W14-D3 | Deploy alert channels (Teams, Slack, email) | Ops | Alerts routed correctly |
| W14-D4 | Test DAG registry auto-discovery | Platform Eng | DAGs auto-discovered |
| W14-D5 | Stress test (100 concurrent tasks) | QA | Performance baseline established |

#### WEEKS 15-16: DAG Migration & SLA Enforcement

| Day | Task | Owner | Deliverable |
|-----|------|-------|------------|
| W15-D1 | Develop DAG generator (lineage_core.py → Airflow DAGs) | Data Eng | Generator script created |
| W15-D2 | Migrate 3 core DAGs (ingest, quality, compliance) | Data Eng | 3 DAGs running in dev |
| W15-D3 | Test DAG execution + lineage tracking | QA | Lineage records verified |
| W15-D4 | Add 7 additional DAGs (costing, geospatial, KPI) | Data Eng | 10 DAGs total, dry-run passed |
| W15-D5 | Dry-run all DAGs with production data sample | QA | Zero failures in dry-run |
| W16-D1 | Implement SLA monitoring (database table + monitor) | Platform Eng | SLA thresholds defined |
| W16-D2 | Integrate SLA checks into DAG callbacks | Platform Eng | SLA breaches trigger alerts |
| W16-D3 | Create SLA dashboard (Power BI) | Analytics | Dashboard shows 99.5% on-time |
| W16-D4 | Documentation + runbooks | Tech Writer | Runbooks published |
| W16-D5 | Go-live preparation (final checklist) | Program Mgr | Ready for production |

#### WEEKS 17-20: Spark Deployment & Integration

| Day | Task | Owner | Deliverable |
|-----|------|-------|------------|
| W17-D1 | Provision Databricks workspace (Azure) | DevOps | Workspace accessible |
| W17-D2 | Create Spark cluster configuration (16 workers, spot instances) | Data Eng | Cluster launches in <2 min |
| W17-D3 | Develop material costing Spark job (test on 1% data) | Data Eng | Job runs in <30 sec on 1% |
| W17-D4 | Develop geospatial joins Spark job (ST_Intersects) | Data Eng | Spatial features generated |
| W17-D5 | Test Spark jobs with 10% data (expected: <5 min) | QA | Performance meets target |
| W18-D1 | Migrate Spark jobs to Databricks notebooks | Data Eng | Notebooks checked into Git |
| W18-D2 | Add incremental processing (Delta Lake, SCD Type 2) | Data Eng | Only new records processed |
| W18-D3 | Add quality validation in Spark (schema checks, outlier detection) | Data Eng | Validation rules enforced |
| W18-D4 | Validation: Spark results vs PostgreSQL (100M records) | QA | Results match within 0.1% |
| W18-D5 | Cost analysis (Spark vs single-machine) | Analytics | 40% cost improvement documented |
| W19-D1 | Create Airflow → Databricks integration (SparkSubmitOperator) | Platform Eng | DAG successfully triggers Spark job |
| W19-D2 | Add Spark job monitoring to SLA framework | Platform Eng | Spark job SLAs tracked |
| W19-D3 | Implement result validation (Spark output → PostgreSQL) | Platform Eng | UPSERT logic working |
| W19-D4 | Performance benchmarking (100M records, measure latency) | QA | <5 min execution time confirmed |
| W19-D5 | Integration testing (end-to-end: Socrata → Spark → API) | QA | Full pipeline validated |
| W20-D1 | Load test Spark cluster (simulate peak load) | QA | Cluster scales to 32 workers |
| W20-D2 | Finalize Spark deployment configuration | DevOps | Prod cluster ready |
| W20-D3 | Documentation (Spark job architecture, troubleshooting) | Tech Writer | Runbooks published |
| W20-D4 | Production readiness review | Program Mgr | Spark approved for prod |
| W20-D5 | Parallel: Start KPI framework design | Analytics | KPI definitions drafted |

#### WEEKS 21-24: Production Hardening & HA/DR

| Day | Task | Owner | Deliverable |
|-----|------|-------|------------|
| W21-D1 | Deploy Azure Cache for Redis (P5, 550 GB) | DevOps | Redis cluster ready |
| W21-D2 | Implement query result caching (1h TTL) | Platform Eng | Query cache decorator created |
| W21-D3 | Implement API response caching (5m TTL) | Platform Eng | API cache decorator created |
| W21-D4 | Load test caching layer (measure hit rate) | QA | >80% hit rate achieved |
| W21-D5 | Deploy PgBouncer (3 replicas, transaction pooling) | DevOps | Connection pooling active |
| W22-D1 | Configure PostgreSQL read replicas (2 additional) | DBA | Replicas synced, lag <1s |
| W22-D2 | Configure geo-replica (secondary region) | DBA | Geo-replica established |
| W22-D3 | Set up WAL archival to Azure Blob Storage | DBA | WAL archived every 5 min |
| W22-D4 | Configure automated failover | DBA | Failover triggers on primary down |
| W22-D5 | Test point-in-time recovery (PITR) | QA | Recovery to arbitrary timestamp works |
| W23-D1 | Create DR runbooks (failover, failback, recovery) | Ops | Runbooks documented + tested |
| W23-D2 | Conduct DR drill #1 (measure RTO/RPO) | Ops | RTO <37 min, RPO <5 min verified |
| W23-D3 | Automate monthly DR drills (Airflow DAG) | Ops | DR drill DAG created |
| W23-D4 | Set up monitoring alerts (SLA, performance, cost) | Ops | Alerts configured in Azure Monitor |
| W23-D5 | Performance optimization (query tuning, index analysis) | DBA | Top 10 slow queries optimized |
| W24-D1 | Create performance dashboard (Azure Monitor) | Ops | Real-time metrics visible |
| W24-D2 | Finalize cost optimization recommendations | Finance | Monthly cost model created |
| W24-D3 | Document all infrastructure (IaC, Terraform) | DevOps | Terraform code checked into Git |
| W24-D4 | Final production readiness review | Program Mgr | All sign-offs complete |
| W24-D5 | Knowledge transfer + team training | Tech Lead | Team trained on systems |

#### POST-IMPLEMENTATION: KPI Framework (Parallel, W20-24)

| Day | Task | Owner | Deliverable |
|-----|------|-------|------------|
| W20-D5 | Define 24 KPI metrics + formulas | Analytics | KPI definitions documented |
| W21-D1 | Create Spark jobs for KPI computation | Data Eng | KPI jobs created |
| W22-D1 | Create Power BI dashboards (24 KPIs) | BI/Analytics | Dashboards published |
| W23-D1 | Set up daily KPI computation (Airflow DAG) | Ops | KPI DAG runs daily |
| W24-D1 | Implement KPI anomaly detection (Azure ML) | Analytics | Anomalies flagged automatically |
| W24-D2 | Create executive scorecard (Teams/SharePoint) | BI/Analytics | Executive scorecard published |
| W24-D3 | Implement trend analysis (YoY, MoM) | Analytics | Trend reports generated |
| W24-D5 | Success metrics tracking + reporting | Program Mgr | Baseline vs Target comparison |

---

## PART 5: RISK MITIGATION STRATEGY

### 5.1 High-Risk Areas & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| **Spark Job Failures** | Data pipeline stops | Medium | Local dev, 10% → 100% rollout, auto-retry, PostgreSQL fallback |
| **Airflow DAG Complexity** | Difficult to maintain | Medium | Auto-generate from lineage, simple templates, peer review |
| **Performance Regression** | Queries 10x slower | Low | Benchmarking before/after, canary deploy, auto-rollback |
| **Cost Overruns** | Budget exceeded | Medium | Cloud cost alerts, spot instances, monthly reviews |
| **Schema Breaking Changes** | API breaks downstream | Low | Schema registry, backward compat checks, deprecation periods |
| **Data Integrity Issues** | Wrong results | Low | Spark vs PostgreSQL validation, quality tests, audit logs |
| **HA/DR Failure** | Cannot recover RTO >1h | Low | Monthly drills, automated failover, runbooks, alerts |

### 5.2 Rollback Procedures

**Rollback Levels:**

**Level 1: DAG Rollback (Airflow)**
- Disable problematic DAG in Airflow UI
- Revert DAG code to previous Git commit
- Re-trigger with `catchup=False`
- Rollback time: <5 minutes

**Level 2: Spark Job Rollback**
- Disable SparkSubmitOperator task in parent DAG
- Fall back to PHASE 2 single-machine query
- Run single-machine query to reconstruct results
- Rollback time: <30 minutes

**Level 3: Database Rollback (PostgreSQL)**
- Use point-in-time recovery (PITR) to restore to previous state
- Azure PostgreSQL: restore to any timestamp in last 35 days
- Rollback time: <1 hour (restore + validation)

**Level 4: Full System Rollback (DR Failover)**
- If primary PostgreSQL fails: failover to geo-replica
- Failover time: <37 minutes (RTO target)
- Recovery point: <5 minutes ago (RPO target)

**Rollback Testing:**
```python
# airflow/dags/test_rollback.py (NEW)
"""Test rollback procedures monthly."""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def test_level_1_rollback():
    """Test DAG rollback."""
    # Disable DAG, revert code, re-enable, verify
    pass

def test_level_2_rollback():
    """Test Spark job rollback."""
    # Disable SparkSubmitOperator, run single-machine query
    pass

def test_level_3_rollback():
    """Test database PITR."""
    # Restore to 1 hour ago, verify data, cleanup
    pass

# Rollback test DAG
with DAG('test_rollback_procedures', schedule_interval='0 3 15 * *') as dag:
    # Runs on 15th of each month
    pass
```

---

## PART 6: RESOURCE & COST ESTIMATION

### 6.1 Team Composition

| Role | Count | Skill Set | Allocation |
|------|-------|-----------|-----------|
| **Senior Data Engineer** | 2 | Spark, Python, distributed systems | 100% (W13-24) |
| **Platform Engineer** | 2 | Airflow, Kubernetes, DevOps | 100% (W13-24) |
| **Solutions Architect** | 1 | HA/DR, cloud design, optimization | 50% (W13-24) |
| **Data Analyst** | 1 | KPI design, analytics, Power BI | 50% (W20-24) |
| **QA Engineer** | 1 | Performance testing, validation | 100% (W13-24) |
| **DevOps/SRE** | 1 | Infrastructure, monitoring, runbooks | 100% (W13-24) |
| **Technical Writer** | 1 | Documentation, runbooks | 50% (W16-24) |

**Total FTE: ~9 FTE for 12 weeks = 108 FTE-weeks**

### 6.2 Infrastructure Costs (Monthly)

#### Development Environment
```
AKS Cluster (2 nodes, Standard_D8s_v3):        $800/month
PostgreSQL (Single server, D2s_v3):             $150/month
Redis (Basic, 1 GB):                            $30/month
Databricks (dev workspace):                     $500/month
                                  Subtotal:    $1,480/month
```

#### Production Environment
```
AKS Cluster (3 nodes, Standard_D32s_v3):      $4,200/month
PostgreSQL Primary + 2 Read Replicas:         $2,000/month
PostgreSQL Geo-Replica (DR):                  $2,000/month
Redis (Premium P5, 550 GB):                   $1,500/month
PgBouncer (3 replicas, managed):              $300/month
Databricks (production workspace):            $2,500/month
Azure Blob Storage (WAL, backups):            $500/month
Azure Monitor / Log Analytics:                $600/month
Bandwidth/Data Transfer:                      $400/month
                                  Subtotal:   $14,000/month
```

#### Annual Cost Breakdown
```
Development (6 months):       $1,480 × 6     = $8,880
Production (6 months):        $14,000 × 6    = $84,000
Infrastructure Subtotal:                       $92,880

Engineering Costs:
  9 FTE × 12 weeks × $150/hr × 40h/week     = $648,000

Total PHASE 3 Cost:                           ~$740,880
```

### 6.3 Cost Optimization Strategies

1. **Use Spot Instances for Spark:** 70% discount = -$1,500/month
2. **Auto-scaling for AKS:** Scale down at night = -$800/month
3. **Reserved Instances (1-year):** 35% discount on PostgreSQL/Redis = -$3,000/month
4. **Databricks Commits:** Pre-buy compute units = -$500/month
5. **Data Transfer Optimization:** Compress logs = -$200/month

**Optimized Annual Cost: ~$720,000**

---

## PART 7: SUCCESS CRITERIA & ACCEPTANCE

### 7.1 PHASE 3 Success Metrics

#### W13-16: Airflow Orchestration
- ✅ 10+ DAGs deployed and running 24/7
- ✅ Lineage integration complete (DAG dependencies auto-generated)
- ✅ SLA monitoring active (99.5% on-time completion)
- ✅ Zero DAG failures in production
- ✅ Airflow uptime >99.9%

#### W17-20: Spark Integration
- ✅ Material costing: 100M records in <5 minutes
- ✅ Geospatial joins operational
- ✅ Spark vs PostgreSQL results match within 0.1%
- ✅ 40% performance improvement documented
- ✅ Cost tracking shows ROI

#### W21-24: Production Hardening
- ✅ Query cache hit rate >80%
- ✅ API response time <500ms (cached)
- ✅ RTO <1 hour verified in DR drills
- ✅ RPO <5 minutes confirmed
- ✅ Uptime SLA >99.9%

#### Post-Implementation: KPI Framework
- ✅ 24 metrics tracked and reported daily
- ✅ Power BI dashboards live and embedded in SharePoint
- ✅ Anomaly detection active
- ✅ Executive scorecard published
- ✅ Trend analysis YoY/MoM

---

## PART 8: DOCUMENTATION & HANDOFF

### 8.1 Documentation Structure

```
docs/phase3/
├── ARCHITECTURE.md              # This document
├── DEPLOYMENT_GUIDE.md          # Step-by-step deployment
├── OPERATIONS_RUNBOOK.md        # Day-2 operations
├── TROUBLESHOOTING.md           # Common issues + fixes
├── PERFORMANCE_TUNING.md        # Query optimization
├── HA_DR_PROCEDURES.md          # Failover + recovery
├── KPI_FRAMEWORK.md             # KPI definitions + computation
├── COST_OPTIMIZATION.md         # Monthly cost reviews
├── SECURITY_HARDENING.md        # Network, auth, encryption
└── KNOWLEDGE_TRANSFER.md        # Training materials
```

### 8.2 Runbook Templates

Each runbook includes:
- **Objective:** What the runbook accomplishes
- **Prerequisites:** Systems/access needed
- **Steps:** Numbered, actionable steps
- **Validation:** How to verify success
- **Rollback:** How to undo if needed
- **Estimated Time:** How long it takes
- **Contacts:** Who to call for help

**Example: Failover Runbook**
```markdown
# PostgreSQL Failover Runbook

## Objective
Promote geo-replica to primary in <37 minutes

## Prerequisites
- Access to Azure portal
- Airflow credentials
- Database credentials

## Steps
1. Verify primary failure (check connection, pg_isready)
2. Notify team (Teams channel: #database-incidents)
3. Azure Portal → PostgreSQL → Promote Geo-Replica
4. Update JDBC connection string in Airflow config
5. Verify new primary responding to queries
6. Monitor for replication lag on secondary

## Validation
- SELECT COUNT(*) from work_orders; (should match baseline)
- Check Azure Monitor for connection spike
- Verify Airflow DAGs auto-reconnecting

## Rollback
- Manual intervention required (restore primary from backup)
- Follow "Recovery After Failover" section

## Estimated Time
37 minutes (RTO target)

## Contacts
- DBA on-call: XXX
- Platform Eng: XXX
- CTO: XXX
```

---

## PART 9: SUCCESS STORIES & FUTURE VISION

### 9.1 Expected Outcomes (End of PHASE 3)

**For NYC DOT Operations:**
- ✅ Ingest 100M+ work orders every 6 hours (Airflow + Spark)
- ✅ Material costing computed in <5 minutes (vs 20+ minutes)
- ✅ ADA compliance checked automatically (compliance DAG)
- ✅ 24 KPIs tracked daily with anomaly detection
- ✅ 99.9% uptime (RTO <1h, RPO <5m with HA/DR)

**For Data Team:**
- ✅ Single source of truth (lineage + schema registry)
- ✅ Self-serve analytics (caching, read replicas)
- ✅ Automated incident response (SLA breaches → alerts)
- ✅ Low operational burden (auto-scaling, auto-healing)

**For Business:**
- ✅ Mission-critical system (enterprise SLA)
- ✅ Faster decision-making (fresh dashboards, hourly KPIs)
- ✅ Cost savings (40% improvement from distributed processing)
- ✅ Regulatory compliance (audit trail, encryption, access control)

### 9.2 PHASE 4 Vision (Beyond W24)

Once PHASE 3 is stable, consider:

1. **Real-Time Streaming (Weeks 25-32)**
   - Replace 6-hour batch with real-time Kafka/Event Hubs
   - Sub-minute latency for KPIs
   - Event-driven orchestration

2. **Advanced Analytics (Weeks 33-40)**
   - Machine learning for demand forecasting
   - Route optimization (Spark MLlib)
   - Predictive maintenance

3. **API Federation (Weeks 41-48)**
   - GraphQL layer for complex queries
   - Multi-tenancy support
   - Rate limiting per tenant

4. **Mobile/Field Operations (Weeks 49-56)**
   - Mobile app for field teams
   - Offline-first sync
   - GPS tracking integration

---

## CONCLUSION

PHASE 3 transforms the NYC DOT data platform from a prototype to an **enterprise-grade distributed system** capable of handling 100M+ records, enforcing SLA compliance, and supporting mission-critical operations 24/7.

By leveraging **Azure-native services** (AKS, PostgreSQL, Databricks, Redis), integrating with **Office 365** (Teams, Power BI), and applying **proven best practices** (Airflow orchestration, Spark distributed processing, HA/DR), PHASE 3 positions the agency for success at scale.

The investment of ~$740K and 108 FTE-weeks delivers a 40% performance improvement, 99.9% uptime, and a solid foundation for future enhancements.

---

**Document Version:** 1.0  
**Last Updated:** May 2026  
**Status:** Ready for Review & Approval  
**Next Step:** Schedule architecture review with stakeholders
