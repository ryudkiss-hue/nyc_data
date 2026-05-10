"""Dashboard templates for observability visualization.

Provides sample dashboard definitions for:
- Prometheus + Grafana
- Datadog
- ELK Stack
- Alert rules

Usage:
    dashboards = DashboardGenerator()
    prometheus_rules = dashboards.prometheus_alert_rules()
    grafana_json = dashboards.grafana_dashboard()
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class DashboardGenerator:
    """Generates dashboard definitions for various platforms."""

    @staticmethod
    def prometheus_alert_rules() -> str:
        """Generate Prometheus alert rules YAML.
        
        Returns:
            YAML string with alert rules
        """
        return """groups:
  - name: observability.rules
    interval: 30s
    rules:
      # Ingestion SLAs
      - alert: IngestionLatencyHighP99
        expr: ingestion_latency_ms{quantile="p99"} > 5000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Ingestion latency P99 exceeds 5s"
          description: "Current P99: {{ $value }}ms"

      - alert: IngestionErrorRateHigh
        expr: rate(ingestion_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Ingestion error rate > 1%"
          description: "Current rate: {{ $value }}"

      # Data Quality SLAs
      - alert: SchemaComplianceLow
        expr: schema_compliance_rate < 0.95
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Schema compliance < 95%"
          description: "Current compliance: {{ $value }}"

      # System SLAs
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage > 90%"
          description: "Current usage: {{ $value | humanizePercentage }}"

      - alert: HighDiskUsage
        expr: node_filesystem_avail_bytes{fstype=~"ext4|xfs"} / node_filesystem_size_bytes < 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk space < 10%"
          description: "Available: {{ $value | humanize }}B"

      - alert: DatabaseConnectionPoolAlmostFull
        expr: db_connection_pool_available / db_connection_pool_size < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database pool > 90% full"
          description: "Available: {{ $value }}"
"""

    @staticmethod
    def grafana_dashboard() -> str:
        """Generate Grafana dashboard JSON.
        
        Returns:
            JSON string with dashboard definition
        """
        dashboard = {
            "dashboard": {
                "title": "NYC Data Engineering Observability",
                "tags": ["observability", "data-pipeline"],
                "timezone": "browser",
                "panels": [
                    {
                        "title": "Ingestion Records/sec",
                        "targets": [
                            {
                                "expr": "rate(ingestion_records_total[1m])",
                                "legendFormat": "records/sec",
                            }
                        ],
                        "type": "graph",
                    },
                    {
                        "title": "Ingestion Latency (ms)",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.99, ingestion_latency_ms)",
                                "legendFormat": "p99",
                            },
                            {
                                "expr": "histogram_quantile(0.95, ingestion_latency_ms)",
                                "legendFormat": "p95",
                            },
                        ],
                        "type": "graph",
                    },
                    {
                        "title": "Data Quality Score",
                        "targets": [
                            {
                                "expr": "schema_compliance_rate * 100",
                                "legendFormat": "compliance %",
                            }
                        ],
                        "type": "gauge",
                    },
                    {
                        "title": "Active Pipelines",
                        "targets": [
                            {
                                "expr": "active_pipelines",
                                "legendFormat": "count",
                            }
                        ],
                        "type": "stat",
                    },
                    {
                        "title": "Error Rate",
                        "targets": [
                            {
                                "expr": "rate(ingestion_errors_total[5m])",
                                "legendFormat": "errors/sec",
                            }
                        ],
                        "type": "graph",
                    },
                    {
                        "title": "Database Pool",
                        "targets": [
                            {
                                "expr": "db_connection_pool_available",
                                "legendFormat": "available",
                            },
                            {
                                "expr": "db_connection_pool_size - db_connection_pool_available",
                                "legendFormat": "in_use",
                            }
                        ],
                        "type": "graph",
                    },
                ],
            }
        }
        return json.dumps(dashboard, indent=2)

    @staticmethod
    def prometheus_scrape_config() -> str:
        """Generate Prometheus scrape configuration.
        
        Returns:
            YAML string with scrape config
        """
        return """scrape_configs:
  - job_name: 'nyc-data-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
    scheme: http

  - job_name: 'nyc-data-pipeline-detailed'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5s
    scrape_timeout: 5s
    metrics_path: '/metrics/detailed'
    scheme: http
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: '(ingestion|transformation|validation|lineage).*'
        action: keep
"""

    @staticmethod
    def datadog_dashboard() -> str:
        """Generate Datadog dashboard JSON.
        
        Returns:
            JSON string with Datadog dashboard
        """
        dashboard = {
            "title": "NYC Data Engineering Pipeline",
            "description": "Observability dashboard for data pipeline",
            "layout_type": "ordered",
            "widgets": [
                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:custom.ingestion.records_per_sec{*}",
                                "display_type": "line",
                            }
                        ],
                        "title": "Ingestion Throughput",
                    }
                },
                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:custom.ingestion.latency_ms{*}",
                                "display_type": "line",
                            }
                        ],
                        "title": "Ingestion Latency",
                    }
                },
                {
                    "definition": {
                        "type": "gauge",
                        "requests": [
                            {
                                "q": "avg:custom.data_quality.compliance_rate{*} * 100",
                            }
                        ],
                        "title": "Data Quality Compliance",
                    }
                },
                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:custom.system.memory_percent{*}",
                                "display_type": "line",
                            }
                        ],
                        "title": "Memory Usage",
                    }
                },
            ],
        }
        return json.dumps(dashboard, indent=2)

    @staticmethod
    def elk_dashboard() -> str:
        """Generate ELK Stack dashboard JSON (Kibana format).
        
        Returns:
            JSON string with Kibana dashboard
        """
        dashboard = {
            "version": "8.0.0",
            "objects": [
                {
                    "id": "nyc-data-overview",
                    "type": "dashboard",
                    "attributes": {
                        "title": "NYC Data Pipeline Overview",
                        "description": "Central observability dashboard",
                        "panels": [
                            {
                                "visualization": "ingestion-latency",
                                "x": 0,
                                "y": 0,
                                "w": 6,
                                "h": 4,
                            },
                            {
                                "visualization": "error-rate",
                                "x": 6,
                                "y": 0,
                                "w": 6,
                                "h": 4,
                            },
                            {
                                "visualization": "data-quality",
                                "x": 0,
                                "y": 4,
                                "w": 6,
                                "h": 4,
                            },
                            {
                                "visualization": "throughput",
                                "x": 6,
                                "y": 4,
                                "w": 6,
                                "h": 4,
                            },
                        ],
                    },
                }
            ],
        }
        return json.dumps(dashboard, indent=2)

    @staticmethod
    def sample_sla_config() -> str:
        """Generate sample SLA configuration YAML.
        
        Returns:
            YAML string with SLA definitions
        """
        return """slas:
  # Ingestion SLAs
  - metric_name: ingestion_latency_p99
    target: 5000  # milliseconds
    window: 5m
    severity: CRITICAL
    channels: [pagerduty, slack]
    description: "Ingestion P99 latency must be < 5 seconds"

  - metric_name: ingestion_success_rate
    target: 0.99  # 99%
    window: 1h
    severity: HIGH
    channels: [slack, email]
    description: "Ingestion success rate must be > 99%"

  # Transformation SLAs
  - metric_name: transformation_latency_p95
    target: 30000  # milliseconds
    window: 5m
    severity: HIGH
    channels: [slack]
    description: "Transformation P95 latency must be < 30 seconds"

  # Data Quality SLAs
  - metric_name: schema_compliance_rate
    target: 0.95  # 95%
    window: 1h
    severity: MEDIUM
    channels: [slack, email]
    description: "Schema compliance must be > 95%"

  - metric_name: ada_compliance_rate
    target: 0.90  # 90%
    window: 1d
    severity: MEDIUM
    channels: [email]
    description: "ADA compliance must be > 90%"

  # API SLAs
  - metric_name: api_response_time_p95
    target: 500  # milliseconds
    window: 5m
    severity: MEDIUM
    channels: [slack]
    description: "API P95 response time must be < 500ms"

  - metric_name: api_uptime
    target: 0.995  # 99.5%
    window: 1d
    severity: CRITICAL
    channels: [pagerduty]
    description: "API uptime must be > 99.5%"

  # Lineage SLAs
  - metric_name: lineage_execution_time_p95
    target: 10000  # milliseconds
    window: 1h
    severity: LOW
    channels: [slack]
    description: "Lineage tracking P95 execution time < 10 seconds"
"""

    @staticmethod
    def sample_prometheus_config() -> str:
        """Generate sample Prometheus configuration.
        
        Returns:
            YAML string with Prometheus config
        """
        return """global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'nyc-data'
    environment: 'production'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - '/etc/prometheus/observability.rules.yml'

scrape_configs:
  - job_name: 'nyc-data-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
"""
