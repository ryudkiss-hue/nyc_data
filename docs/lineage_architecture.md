# Data Lineage System - Technical Architecture

## System Overview

The data lineage system is a production-grade component that tracks complete data provenance through the NYC data engineering platform. It provides visibility into data transformations, dependencies, execution history, and impact analysis.

```
┌─────────────────────────────────────────────────────────────────┐
│                       Integration Points                         │
├─────────────────────────────────────────────────────────────────┤
│  Client (ingest)   │  Pipeline (transform)   │  Persistence     │
│     ↓              │         ↓               │     (sink)       │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                  Automatic Tracking Layer                    │ │
│ │  (lineage_tracking.py - decorators & context managers)       │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                            ↓                                      │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                     Core Lineage DAG                         │ │
│ │  (lineage_core.py - nodes, edges, graph operations)         │ │
│ └──────────────────────────────────────────────────────────────┘ │
│        ↓           ↓              ↓             ↓               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Queries  │ │ Persist  │ │ Impact   │ │ Visualiz │          │
│  │ (Q.py)   │ │ (P.py)   │ │ (I.py)   │ │ (V.py)   │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│        │           │              │             │               │
│        └───────────┴──────────────┴─────────────┘               │
│                          ↓                                        │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                 PostgreSQL Persistence                       │ │
│ │  Tables: lineage_nodes, lineage_edges, execution_history    │ │
│ └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Lineage Core (`lineage_core.py`)

**Purpose**: Data model and directed acyclic graph (DAG) operations

**Key Classes**:

- **`TransformationNode`**: Represents data sources, transformations, and sinks
  - Attributes: id, name, type, owner, inputs, outputs, execution_history
  - Methods: record_execution, get_latest_execution, get_execution_history
  - Serializable to/from JSON

- **`ExecutionRecord`**: Tracks a single transformation execution
  - Captures: status, timestamps, row counts, duration, errors, quality metrics
  - Used for audit trail and performance analysis
  - Immutable once created

- **`LineageEdge`**: Represents dependencies between nodes
  - Types: DEPENDENCY, DATA_FLOW, SCHEMA_DEPENDENCY
  - Cardinality: 1:1, 1:N, N:1, N:N
  - Optional: join keys, filter conditions

- **`DAG`**: Directed acyclic graph container
  - Uses NetworkX for graph operations
  - Operations: add_node, add_edge, remove_node
  - Queries: get_upstream_dependencies, get_downstream_consumers
  - Analysis: get_critical_path, get_impact_scope, validate

**Design Rationale**:
- Immutable execution records prevent data loss
- Dataclass-based for memory efficiency
- NetworkX integration for standard graph algorithms
- Full JSON serialization for API serving

### 2. Lineage Tracking (`lineage_tracking.py`)

**Purpose**: Automatic tracking integration with existing code

**Key Functions**:

- **`@track_transformation()`**: Decorator for auto-tracking functions
  - Records execution metrics automatically
  - Captures input/output row counts and duration
  - Handles exceptions and logs errors
  - Example: `@track_transformation(inputs=['raw'], outputs=['clean'])`

- **`lineage_context()`**: Context manager for code blocks
  - Tracks execution within `with` statements
  - Useful for inline transformations
  - Example: `with lineage_context('aggregation', inputs, outputs):`

- **`register_*_node()`**: Helper functions for common node types
  - `register_ingestion_node()` - Data sources
  - `register_sink_node()` - Persistence targets
  - `register_validation_node()` - Quality checks

- **Global persistence**: `set_global_persistence()` for persistence layer

**Design Rationale**:
- Backward compatible: existing code works without changes
- Minimal boilerplate: simple decorators and context managers
- Automatic metric collection: no manual instrumentation needed
- Optional persistence: can work in-memory or with database

### 3. Lineage Persistence (`lineage_persistence.py`)

**Purpose**: PostgreSQL storage for lineage data

**Key Classes**:

- **`LineagePersistence`**: Database operations layer
  - CRUD: save_node, get_node, save_edge, save_execution
  - Queries: get_execution_history, get_edges
  - Exports: export_dag (JSON, GraphML, Mermaid, DOT)
  - Audit logging: automatic for all changes

**PostgreSQL Schema**:

```
lineage_nodes
├── id (PK)
├── node_id (unique)
├── name, node_type
├── owner, created_at, last_modified
├── configuration (JSONB)
└── tags (JSONB)

lineage_edges
├── id (PK)
├── source_node_id (FK)
├── target_node_id (FK)
├── edge_type, cardinality
├── join_keys (JSONB)
└── filter_conditions

lineage_execution_history
├── id (PK)
├── execution_id (unique)
├── node_id (FK)
├── started_at, completed_at
├── status, duration_seconds
├── input/output row counts
├── error_message
├── data_quality_metrics (JSONB)
└── executed_by, notes

lineage_audit_log
├── id (PK)
├── event_type, node_id
├── old_value, new_value
├── created_by, created_at
└── change_details (JSONB)
```

**Indexing Strategy**:
- Primary lookups: node_id, execution_id, status
- Range queries: created_at, started_at
- JSON queries: GIN indexes on tags, configuration, metrics

**Design Rationale**:
- Event sourcing: audit log captures all changes
- JSON for flexibility: configuration and metrics are dynamic
- Cascading deletes: removing node cleans up edges and executions
- Batch operations: prepared for multi-node transactions

### 4. Lineage Query (`lineage_query.py`)

**Purpose**: Unified query interface for lineage discovery

**Key Methods**:

```python
find_sources(node_id)           # What feeds into this node?
find_consumers(node_id)         # What depends on this node?
find_path(source, target)       # Transformation path between nodes
find_all_paths(source, target)  # All transformation paths
search_nodes(...)               # Search by name, type, owner, tag
get_node_info(node_id)          # Complete node details
get_freshness(node_id)          # Data age and staleness
get_completeness(node_id)       # Quality metrics
find_by_tag(tag)                # Find all nodes with tag
find_by_owner(owner)            # Find all nodes owned by user
find_by_type(type)              # Find all nodes of type
get_statistics()                # Overall DAG metrics
validate_lineage()              # Check DAG integrity
```

**Query Performance**:
- Upstream/downstream: O(V + E) using NetworkX BFS
- Path finding: O(V + E) using Dijkstra
- Search: O(V) with linear scan (acceptable for ~1000 nodes)
- Target: <500ms for typical DAGs

**Design Rationale**:
- Simple API: straightforward method names and signatures
- Composable: combine multiple queries for complex analysis
- Efficient: leverages NetworkX graph algorithms
- Extensible: easy to add new query methods

### 5. Lineage Impact (`lineage_impact.py`)

**Purpose**: Analyze downstream effects of changes

**Key Classes**:

- **`ImpactReport`**: Results of impact analysis
  - affected_nodes: All downstream nodes
  - affected_users: Users/teams to notify
  - breaking_changes: Schema changes detected
  - critical_paths: Dependency chains that break
  - remediation_steps: How to mitigate
  - risk_score: 0-100 severity assessment

- **`ImpactAnalysis`**: Impact analysis engine
  - analyze_change(node_id) → ImpactReport
  - find_breaking_changes(old_schema, new_schema) → List[BreakingChange]
  - estimate_downstream_impact(node_id) → Dict[node_id → score]

**Breaking Change Detection**:

| Change Type | Severity | Example |
|-------------|----------|---------|
| Column deletion | CRITICAL | id column removed |
| Type change | HIGH | int → string conversion |
| Null constraint | HIGH | nullable=True → False |
| Rename | HIGH | old_name → new_name |
| Position change | LOW | column reordered |

**Risk Scoring Algorithm**:
```
risk_score = (
    node_count_factor(affected_count) +
    critical_path_factor(critical_path_count) +
    sink_impact_factor(sink_nodes_affected)
) / 3

Where:
- node_count_factor: min(100, count * 5)
- critical_path_factor: count * 10
- sink_impact_factor: sum(15 for each sink)
```

**Design Rationale**:
- Schema-aware: integrates with schema registry
- User-centric: identifies affected teams
- Actionable: provides remediation steps
- Quantified: risk scores guide prioritization

### 6. Lineage Visualization (`lineage_visualization.py`)

**Purpose**: Export and visualization of lineage data

**Export Formats**:

| Format | Tool Support | Use Case |
|--------|--------------|----------|
| JSON | APIs, databases | Data interchange, warehousing |
| GraphML | Gephi, yEd, Cytoscape | Interactive analysis |
| Mermaid | GitHub, documentation | Markdown embedding |
| DOT | Graphviz | Publication-quality diagrams |
| ASCII | Terminal | Quick inspection |
| HTML | Browsers | Web dashboard |

**Key Methods**:

- `to_json()` - Complete JSON dump
- `to_graphml()` - GraphML for graph tools
- `to_mermaid()` - Mermaid diagram syntax
- `to_dot()` - Graphviz DOT format
- `to_ascii()` - Terminal visualization
- `to_html_table()` - HTML table representation
- `get_subgraph(node_id)` - Extract neighborhood DAG
- `get_execution_summary()` - Execution statistics

**Design Rationale**:
- Multi-format: choose format for specific use case
- Subgraph extraction: focus on specific areas
- Lossless JSON: can reconstruct full DAG
- Tool compatibility: integrate with existing visualization software

## Data Flow

### Ingestion Lineage

```
Socrata API
    ↓
client.py (query_socrata)
    ↓
[Register ingestion node]
    ↓
save_node(ingest_construction)
    ↓
PostgreSQL lineage_nodes
```

### Transformation Lineage

```
@track_transformation(...)
def clean_data(df):
    return df.dropna()
    ↓
Execution starts
    ↓
ExecutionRecord created
    ↓
save_execution() → PostgreSQL
    ↓
Node execution_history updated
```

### Persistence Lineage

```
PostgresExporter.write()
    ↓
[Register sink node]
    ↓
add_edge(transform → sink)
    ↓
save_edge() → PostgreSQL
```

## Integration Points

### With Schema Registry

```python
# Link lineage to schema versions
schema_version = registry.register_dataset(...)
node.schema_version = schema_version.version_id
persistence.save_node(node)

# Detect schema-breaking changes
old_schema = registry.get_schema(node_id, version=1)
new_schema = registry.get_schema(node_id, version=2)
breaking_changes = analyzer.find_breaking_changes(old_schema, new_schema, node_id)
```

### With Validation Engine

```python
# Register validation transformation
validation_node = register_validation_node(
    'data_quality_check',
    'Quality validation',
    input_dataset='transform.raw_data',
    rules={'nulls': 0.05, 'duplicates': 0.01}
)

# Record validation execution
validation_node.record_execution(
    status=ExecutionStatus.SUCCESS,
    metrics={'null_percentage': 0.02, 'duplicate_percentage': 0},
    output_rows=len(df)
)
```

### With Pipeline Engine

```python
# Auto-track pipeline runs
@track_transformation(inputs=['raw'], outputs=['clean'])
def pipeline_step():
    df = pd.read_csv('raw.csv')
    df = df.dropna()
    df.to_csv('clean.csv')
    return df

# Metrics auto-collected: timing, row counts
```

### With Airflow DAGs

```python
# Airflow task → Lineage node
task = PythonOperator(
    task_id='clean_data',
    python_callable=clean_data_func
)

# Map task dependencies to lineage edges
# Infer node connections from DAG topology
```

## Query Optimization

### For Large DAGs (5000+ nodes)

1. **Limit depth**: restrict upstream/downstream traversal
   ```python
   get_upstream_dependencies(node_id, max_depth=3)
   ```

2. **Materialized paths**: pre-compute critical paths
   ```python
   # Cache result for frequent queries
   critical_paths[node_id] = calculate_once()
   ```

3. **Lazy loading**: load execution history on demand
   ```python
   node = get_node(node_id)  # Metadata only
   history = get_execution_history(node_id)  # On demand
   ```

4. **Database indexes**: leverage PostgreSQL GIN indexes
   ```sql
   CREATE INDEX idx_tags ON lineage_nodes USING GIN (tags)
   ```

## Thread Safety

- **Node creation**: Use lock for add_node operations
- **Execution recording**: Append-only execution history
- **Persistence**: Connection pooling handles concurrency
- **Audit log**: All writes are serialized via database transactions

## Disaster Recovery

- **Audit trail**: Complete history in lineage_audit_log
- **Point-in-time recovery**: Can reconstruct DAG at any timestamp
- **Cascading deletes**: Integrity maintained via foreign keys
- **Backups**: Standard PostgreSQL backup procedures

## Future Enhancements

1. **Real-time tracking**: Event streaming with Kafka
2. **ML-based impact prediction**: Learn impact patterns
3. **Interactive web UI**: Dashboard for lineage exploration
4. **Data quality alerting**: Anomaly detection in metrics
5. **Federated lineage**: Connect multiple data platforms
6. **Column-level lineage**: Track individual column transformations
7. **Cost attribution**: Allocate compute costs to lineage chains
8. **Lineage replay**: Execute transformation chains from history

## Performance Benchmarks

| Operation | Time | DAG Size |
|-----------|------|----------|
| Add node | <1ms | N/A |
| Add edge | <1ms | 1000 nodes |
| Get upstream deps | 5ms | 1000 nodes |
| Find path | 10ms | 1000 nodes |
| Export JSON | 50ms | 1000 nodes |
| Full DAG validation | 20ms | 1000 nodes |

## Security Considerations

- **Access control**: Audit log captures who changed lineage
- **Data privacy**: Configuration field supports encrypted secrets
- **Compliance**: Audit trail for regulatory requirements
- **Immutability**: Execution records cannot be modified (only appended)

## Dependencies

### Required
- Python 3.9+
- NetworkX 3.3+ (graph algorithms)
- psycopg 3.3+ (PostgreSQL driver)

### Optional
- Graphviz (for DOT export rendering)
- Gephi (for GraphML visualization)

## Error Handling

| Error | Root Cause | Resolution |
|-------|-----------|------------|
| "Cycle detected" | Circular dependency | Review path, remove edge |
| "Node not found" | Referencing nonexistent node | Create node first |
| "Connection failed" | Database unavailable | Check PostgreSQL connection |
| "Invalid schema" | Bad node configuration | Validate node properties |

See [`lineage.md`](lineage.md) for user guide and usage examples.
