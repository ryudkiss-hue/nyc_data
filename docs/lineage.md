# Data Lineage and Transformation DAG Tracking

Complete guide to the data lineage system for the NYC Data Engineering toolkit.

## Overview

The data lineage system tracks complete provenance for data flowing through the NYC data engineering platform, from ingestion through serving. It provides:

- **Transformation Tracking**: Automatic recording of all data transformations
- **Dependency Graphs**: Visualization of data dependencies as DAGs
- **Audit Trails**: Complete execution history with timestamps and users
- **Impact Analysis**: Understand downstream effects of changes
- **Schema Linking**: Integration with schema registry versions
- **Multiple Exports**: JSON, GraphML, Mermaid, DOT, and ASCII formats

## Quick Start

### Basic Lineage Query

```python
from socrata_toolkit.lineage_core import DAG
from socrata_toolkit.lineage_query import LineageQuery

# Load lineage DAG
dag = DAG()

# Create query interface
query = LineageQuery(dag)

# Find what feeds into a transformation
sources = query.find_sources('transform.construction_cleaning')
# Returns: ['ingest.socrata_construction_list', 'ingest.complaints']

# Find what depends on this data
consumers = query.find_consumers('ingest.socrata_construction_list')
# Returns: ['transform.construction_cleaning', 'transform.complaints_analysis', 'sink.warehouse']

# Get complete path between nodes
path = query.find_path('ingest.construction_list', 'sink.reporting_db')
# Returns: ['ingest.construction_list', 'transform.clean', 'transform.aggregate', 'sink.reporting_db']
```

### Register Transformation Nodes

```python
from socrata_toolkit.lineage_tracking import (
    register_ingestion_node,
    register_sink_node,
    track_transformation,
)

# Register an ingestion source
ingest_node = register_ingestion_node(
    dataset_id='4qqp-zixf',
    dataset_name='NYC Construction List',
    source='socrata',
    owner='data-eng@nyc.gov',
    schema_version='construction_v2.1'
)

# Auto-track a transformation function
@track_transformation(
    inputs=['ingest.construction_list'],
    outputs=['transform.construction_clean'],
    owner='data-eng@nyc.gov',
    tags=['daily', 'production']
)
def clean_construction_data(df):
    """Clean and validate construction data."""
    return df.dropna(subset=['id', 'project_name'])

# Use with context manager
from socrata_toolkit.lineage_tracking import lineage_context

with lineage_context(
    'daily_aggregation',
    inputs=['transform.construction_clean'],
    outputs=['transform.construction_daily'],
    owner='analytics@nyc.gov'
):
    result = expensive_aggregation_function()
```

### Analyze Impact of Changes

```python
from socrata_toolkit.lineage_impact import ImpactAnalysis

analyzer = ImpactAnalysis(dag)

# Analyze what breaks if you change a dataset
report = analyzer.analyze_change('ingest.construction_list')

print(f"Affected nodes: {report.affected_count}")
print(f"Affected users: {report.affected_users}")
print(f"Risk score: {report.risk_score}/100")
print(f"Estimated remediation effort: {report.estimated_effort_hours} hours")

# Get detailed remediation steps
for step in report.remediation_steps:
    print(f"- {step}")
```

### Export and Visualize

```python
from socrata_toolkit.lineage_visualization import LineageVisualizer

viz = LineageVisualizer(dag)

# Export as JSON (most complete format)
json_export = viz.to_json()

# Export for visualization tools
graphml = viz.to_graphml()  # For Gephi, yEd
mermaid = viz.to_mermaid()  # For GitHub/Markdown
dot = viz.to_dot()          # For Graphviz

# Terminal-friendly ASCII diagram
print(viz.to_ascii())

# Extract subgraph around specific node
subgraph = viz.get_subgraph('transform.construction_clean')
```

## CLI Commands

### List and View Nodes

```bash
# List all nodes
socrata lineage nodes

# Filter by type
socrata lineage nodes --type sink

# Filter by owner
socrata lineage nodes --owner data-eng@nyc.gov

# Filter by tag
socrata lineage nodes --tag production

# Output as JSON
socrata lineage nodes --json | jq '.nodes[] | select(.type == "sink")'
```

### View Node Details

```bash
# Show details for a specific node
socrata lineage node transform.construction_clean

# Show with full execution history
socrata lineage node transform.construction_clean --full
```

### Find Dependencies

```bash
# Show what feeds into a node
socrata lineage sources transform.construction_clean

# Show what depends on a node
socrata lineage consumers ingest.construction_list

# Find shortest path between nodes
socrata lineage path ingest.construction_list sink.warehouse

# Analyze impact of change
socrata lineage impact ingest.construction_list
```

### Export and Analyze

```bash
# Export complete DAG
socrata lineage dag --format json --output lineage.json
socrata lineage dag --format mermaid --output lineage.md
socrata lineage dag --format graphml --output lineage.graphml
socrata lineage dag --format ascii

# Check data freshness
socrata lineage freshness ingest.construction_list --stale-hours 24

# Show DAG statistics
socrata lineage stats
```

## Integration with Existing Code

### With Pipeline.py

The lineage system integrates automatically with `pipeline.py`:

```python
from socrata_toolkit.lineage_tracking import set_global_persistence
from socrata_toolkit.pipeline import run_from_rows

# Set up persistence (optional, for permanent storage)
# persistence = LineagePersistence(db_connection)
# set_global_persistence(persistence)

# Run pipeline - lineage is automatically tracked
rows = fetch_data()
result = run_from_rows(rows, targets={
    'postgres': {'table': 'construction_list', ...},
    'mongo': {'database': 'nyc_data', ...}
})
```

### With Schema Registry

Link lineage nodes to schema versions:

```python
from socrata_toolkit.lineage_tracking import register_ingestion_node
from socrata_toolkit.schema_registry import SchemaRegistry

registry = SchemaRegistry()

# Capture schema for dataset
schema_version = registry.register_dataset(
    dataset_id='construction_list',
    rows=sample_data
)

# Link to lineage node
ingest_node = register_ingestion_node(
    dataset_id='construction_list',
    dataset_name='NYC Construction List',
    schema_version=schema_version.version_id
)
```

### With Validation Engine

Track data quality checks:

```python
from socrata_toolkit.lineage_tracking import register_validation_node
from socrata_toolkit.validation import validate_required_columns

# Register validation node
validation_node = register_validation_node(
    validation_id='construction_required_cols',
    validation_name='Required Column Check',
    input_dataset='transform.construction_clean',
    rules={
        'required_columns': ['id', 'project_name', 'location'],
        'null_threshold': 0.05,
    },
    owner='data-eng@nyc.gov'
)

# Run validation
try:
    validate_required_columns(df, ['id', 'project_name', 'location'])
    # Record success
    validation_node.record_execution(
        status=ExecutionStatus.SUCCESS,
        output_rows=len(df)
    )
except Exception as e:
    # Record failure
    validation_node.record_execution(
        status=ExecutionStatus.FAILED,
        error_msg=str(e)
    )
```

## Node Types

| Type | Purpose | Examples |
|------|---------|----------|
| `INGESTION` | Data source | Socrata datasets, APIs, files |
| `TRANSFORMATION` | Data processing | Cleaning, joining, filtering |
| `AGGREGATION` | Summarization | GROUP BY, pivot tables |
| `VALIDATION` | Quality checks | Null checks, uniqueness, range |
| `MATERIALIZATION` | Intermediate view | Cached tables, marts |
| `SINK` | Data target | PostgreSQL, MongoDB, files |

## Execution History and Metrics

Track execution performance and data quality:

```python
from socrata_toolkit.lineage_core import ExecutionStatus

# Record transformation execution
node.record_execution(
    status=ExecutionStatus.SUCCESS,
    input_rows=1000,
    output_rows=950,
    duration_secs=12.5,
    metrics={
        'null_percentage': 2.5,
        'duplicate_percentage': 0.1,
        'outlier_count': 3,
    },
    user='scheduler@example.com',
    notes='Daily run on 2026-05-10'
)

# Query execution history
for execution in node.get_execution_history(limit=20):
    print(f"{execution.status.value}: {execution.duration_seconds}s")
    print(f"  Rows: {execution.input_row_count} → {execution.output_row_count}")
    if execution.error_message:
        print(f"  Error: {execution.error_message}")
```

## Export Formats

### JSON (Complete)
Contains all nodes, edges, execution history, and metadata. Best for:
- API serving
- Data warehousing
- Detailed analysis

### GraphML (Visualization Tools)
Compatible with Gephi, yEd, Cytoscape. Best for:
- Interactive graph exploration
- Network analysis
- Layout algorithms

### Mermaid (GitHub/Markdown)
Embeddable in documentation. Best for:
- README files
- Architecture documents
- Quick visualization

### DOT (Graphviz)
Process with Graphviz tools. Best for:
- Custom rendering
- Publication-quality diagrams
- Automated layout

### ASCII (Terminal)
Text-based visualization. Best for:
- CLI inspection
- Log files
- Quick checks

## Querying Lineage

### Search by Multiple Criteria

```python
from socrata_toolkit.lineage_query import LineageQuery

query = LineageQuery(dag)

# Search with multiple filters
nodes = query.search_nodes(
    name='construction',  # Substring match
    node_type='transformation',
    owner='data-eng@nyc.gov',
    tag='daily'
)

# Find by single attribute
daily_nodes = query.find_by_tag('daily')
owned_by_user = query.find_by_owner('data-eng@nyc.gov')
sinks = query.find_by_type('sink')
```

### Data Freshness Analysis

```python
# Check staleness of data
freshness = query.get_freshness(
    'ingest.construction_list',
    stale_threshold_hours=24
)

if freshness.is_stale:
    print(f"Data is {freshness.age_seconds/3600:.1f} hours old")
    print("Requires refresh!")
else:
    print(f"Data is fresh (last updated {freshness.last_execution_time})")
```

### Completeness Metrics

```python
# Analyze data completeness
metrics = query.get_completeness('transform.construction_clean')

print(f"Success rate: {metrics['success_rate']*100:.1f}%")
print(f"Average quality score: {metrics['average_quality_score']:.1f}/100")
print(f"Total rows processed: {metrics['total_rows_processed']}")

if metrics['recent_issues']:
    print("Recent issues:")
    for issue in metrics['recent_issues']:
        print(f"  - {issue['error']}")
```

## Best Practices

1. **Name nodes descriptively**: Use clear, hierarchical naming
   - ✅ `ingest.socrata.construction_list`
   - ❌ `step1`, `transform_xyz`

2. **Tag for organization**: Use consistent tags for filtering
   - `daily`, `weekly`, `monthly` (frequency)
   - `production`, `staging` (environment)
   - `high-priority`, `low-priority` (importance)

3. **Record owner information**: Always specify node owners
   - Facilitates impact communication
   - Enables ownership-based queries

4. **Track execution metrics**: Record row counts and timing
   - Identifies performance regressions
   - Supports SLA tracking

5. **Link to schema versions**: Connect nodes to schema registry
   - Supports breaking change detection
   - Enables schema-aware impact analysis

6. **Document transformations**: Add descriptions to nodes
   - Explains transformation logic
   - Aids new team member onboarding

## Troubleshooting

### Cycles Detected
Error: "Edge would create a cycle"

**Solution**: Check for circular dependencies. DAGs must be acyclic.
```python
# Review the path that creates the cycle
path = query.find_all_paths(target_id, source_id)
# Remove the problematic edge
dag.remove_edge(source_id, target_id)
```

### Missing Nodes
Error: "Node X does not exist"

**Solution**: Ensure node is created before adding edges
```python
# Create node first
node = TransformationNode(node_id='transform.xyz', name='Transform XYZ')
dag.add_node(node)
# Then add edges
dag.add_edge('source', 'transform.xyz')
```

### Stale Data Alerts
"Data is X hours old, exceeds threshold of Y hours"

**Solution**: Check execution history and rerun pipeline
```python
# View recent executions
history = node.get_execution_history(limit=5)
for exec in history:
    if exec.status.value == 'failed':
        print(f"Failed execution: {exec.error_message}")
        # Trigger re-run
```

## Performance Considerations

- **Query performance**: < 500ms for typical DAGs with 1000+ nodes
- **Memory usage**: ~1KB per node + execution record
- **Persistence**: Batch writes to PostgreSQL for efficiency
- **Visualization**: Large DAGs (5000+ nodes) may be slow in browsers

## See Also

- [`docs/lineage_architecture.md`](lineage_architecture.md) - Technical design
- [`socrata_toolkit/lineage_core.py`](../socrata_toolkit/lineage_core.py) - Core API
- [`socrata_toolkit/lineage_query.py`](../socrata_toolkit/lineage_query.py) - Query interface
- [`tests/test_lineage.py`](../tests/test_lineage.py) - Test examples
