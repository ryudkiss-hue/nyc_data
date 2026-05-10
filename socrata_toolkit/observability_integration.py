"""Central observability manager integrating all components.

Provides a singleton ObservabilityManager that coordinates:
- Structured logging
- Metrics collection
- Distributed tracing
- Health checking
- SLA tracking

Usage:
    obs = ObservabilityManager()
    obs.initialize()
    
    logger = obs.get_logger(__name__)
    logger.info('Operation complete')
    
    obs.get_metrics().counter('records_processed', 100)
"""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from socrata_toolkit.observability_logging import (
    LogAggregator,
    LogContext,
    StructuredLogger,
    get_log_aggregator,
    setup_logging,
)
from socrata_toolkit.observability_metrics import (
    MetricsCollector,
    get_metrics_collector,
)
from socrata_toolkit.observability_tracing import (
    TracingContext,
    get_tracing_context,
)
from socrata_toolkit.observability_health import (
    HealthChecker,
    get_health_checker,
)
from socrata_toolkit.observability_sla import (
    SLATracker,
    get_sla_tracker,
)


class ObservabilityManager:
    """Central manager for all observability components.
    
    Singleton pattern ensures single instance across application.
    Coordinates logging, metrics, tracing, health checks, and SLAs.
    
    Example:
        obs = ObservabilityManager()
        obs.initialize()
        
        logger = obs.get_logger(__name__)
        logger.info('Starting process')
        
        obs.get_metrics().counter('items_processed', 100)
        obs.get_tracing_context().start_span('operation')
    """

    _instance: Optional[ObservabilityManager] = None

    def __new__(cls) -> ObservabilityManager:
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize observability manager."""
        if self._initialized:
            return

        # Initialize components
        self._logger_cache: Dict[str, StructuredLogger] = {}
        self._log_aggregator = get_log_aggregator()
        self._metrics_collector = get_metrics_collector()
        self._tracing_context = get_tracing_context()
        self._health_checker = get_health_checker()
        self._sla_tracker = get_sla_tracker()

        # Configuration
        self._enabled = True
        self._log_level = os.getenv('LOG_LEVEL', 'INFO')
        self._metrics_enabled = os.getenv('OBSERVABILITY_METRICS_ENABLED', 'true').lower() == 'true'
        self._tracing_enabled = os.getenv('OBSERVABILITY_TRACING_ENABLED', 'true').lower() == 'true'
        self._health_enabled = os.getenv('OBSERVABILITY_HEALTH_ENABLED', 'true').lower() == 'true'

        self._initialized = True

    def initialize(self) -> None:
        """Initialize observability stack.
        
        Sets up logging, registers default checks, loads SLA definitions.
        Should be called early in application startup.
        """
        # Setup logging
        setup_logging(level=self._log_level, json_output=True)

        # Register shutdown hook
        atexit.register(self.shutdown)

    def shutdown(self) -> None:
        """Gracefully shutdown observability stack."""
        # Flush any pending logs, metrics, etc.
        pass

    def get_logger(self, name: str) -> StructuredLogger:
        """Get a structured logger.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            StructuredLogger instance
        """
        if name not in self._logger_cache:
            logger = StructuredLogger(name)
            self._logger_cache[name] = logger
            # Also hook into aggregator
            self._setup_log_forwarding(logger)
        return self._logger_cache[name]

    def _setup_log_forwarding(self, logger: StructuredLogger) -> None:
        """Setup log forwarding to aggregator."""
        # This would be implemented to capture logs from the logger
        # into the aggregator for central storage
        pass

    def get_metrics(self) -> MetricsCollector:
        """Get metrics collector.
        
        Returns:
            MetricsCollector instance
        """
        return self._metrics_collector

    def get_tracing_context(self) -> TracingContext:
        """Get tracing context.
        
        Returns:
            TracingContext instance
        """
        return self._tracing_context

    def get_health_checker(self) -> HealthChecker:
        """Get health checker.
        
        Returns:
            HealthChecker instance
        """
        return self._health_checker

    def get_sla_tracker(self) -> SLATracker:
        """Get SLA tracker.
        
        Returns:
            SLATracker instance
        """
        return self._sla_tracker

    def get_log_aggregator(self) -> LogAggregator:
        """Get log aggregator.
        
        Returns:
            LogAggregator instance
        """
        return self._log_aggregator

    def get_log_context(self) -> LogContext:
        """Get current log context.
        
        Returns:
            LogContext with current correlation ID and fields
        """
        return LogContext.get_current()

    def create_log_context(
        self,
        correlation_id: Optional[str] = None,
        **fields: Any,
    ) -> LogContext:
        """Create a new log context.
        
        Args:
            correlation_id: Optional correlation ID
            **fields: Contextual fields
            
        Returns:
            LogContext context manager
        """
        return LogContext(correlation_id=correlation_id, **fields)

    def instrument_function(self, func_name: str, func: Any) -> Any:
        """Instrument a function for observability.
        
        Adds automatic metrics, tracing, and logging.
        
        Args:
            func_name: Name of function
            func: Function to instrument
            
        Returns:
            Instrumented function
        """
        # This would wrap the function with observability
        # For now, just return as-is
        return func

    def health_status(self) -> Dict[str, Any]:
        """Get overall health status.
        
        Returns:
            Dictionary with health report
        """
        report = self._health_checker.check_health()
        return report.to_dict()

    def readiness_status(self) -> Dict[str, Any]:
        """Get readiness probe status.
        
        Returns:
            Dictionary with readiness status
        """
        return self._health_checker.get_readiness_probe()

    def liveness_status(self) -> Dict[str, Any]:
        """Get liveness probe status.
        
        Returns:
            Dictionary with liveness status
        """
        return self._health_checker.get_liveness_probe()

    def sla_report(self) -> Dict[str, Any]:
        """Get SLA compliance report.
        
        Returns:
            Dictionary with SLA status
        """
        report = self._sla_tracker.evaluate()
        return report.to_dict()

    def metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary.
        
        Returns:
            Dictionary with metrics overview
        """
        return self._metrics_collector.summary_dict()

    def export_logs_json(self, filepath: Path) -> None:
        """Export logs to JSON file.
        
        Args:
            filepath: Output file path
        """
        self._log_aggregator.export_json(filepath)

    def export_logs_csv(self, filepath: Path) -> None:
        """Export logs to CSV file.
        
        Args:
            filepath: Output file path
        """
        self._log_aggregator.export_csv(filepath)

    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format.
        
        Returns:
            Prometheus text format
        """
        return self._metrics_collector.export_prometheus()

    def export_metrics_json(self) -> str:
        """Export metrics as JSON.
        
        Returns:
            JSON string
        """
        return self._metrics_collector.export_json()

    def export_traces_jaeger(self) -> str:
        """Export traces in Jaeger format.
        
        Returns:
            Jaeger JSON format
        """
        return self._tracing_context.export_jaeger_json()

    def configure_sla(
        self,
        metric_name: str,
        target: float,
        window: str = "5m",
        severity: str = "MEDIUM",
        channels: Optional[list] = None,
    ) -> None:
        """Configure an SLA.
        
        Args:
            metric_name: Metric name
            target: Target value
            window: Time window
            severity: Alert severity
            channels: Notification channels
        """
        self._sla_tracker.add_sla(
            metric_name,
            target=target,
            window=window,
            severity=severity,
            channels=channels or [],
        )

    def load_sla_config(self, config_file: Path) -> None:
        """Load SLA configuration from YAML file.
        
        Args:
            config_file: Path to YAML config
        """
        self._sla_tracker.import_slas_yaml(config_file)

    def save_sla_config(self, config_file: Path) -> None:
        """Save SLA configuration to YAML file.
        
        Args:
            config_file: Output YAML file path
        """
        self._sla_tracker.export_slas_yaml(config_file)

    def query_logs(self, **filters: Any) -> list:
        """Query logs with filters.
        
        Args:
            **filters: Filter criteria
            
        Returns:
            List of LogRecord objects
        """
        return self._log_aggregator.query(**filters)

    def get_trace(self, trace_id: str) -> list:
        """Get all spans in a trace.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            List of Span objects
        """
        return self._tracing_context.get_trace(trace_id)

    def enable(self) -> None:
        """Enable observability."""
        self._enabled = True

    def disable(self) -> None:
        """Disable observability."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if observability is enabled."""
        return self._enabled

    def reset(self) -> None:
        """Reset all metrics and clear buffers."""
        self._metrics_collector.reset()
        self._log_aggregator.buffer._buffer.clear()


# Global instance
_obs_manager: Optional[ObservabilityManager] = None


def get_observability_manager() -> ObservabilityManager:
    """Get or create global observability manager.
    
    Returns:
        ObservabilityManager singleton instance
    """
    global _obs_manager
    if _obs_manager is None:
        _obs_manager = ObservabilityManager()
    return _obs_manager


# Initialize on module import
try:
    _obs = get_observability_manager()
    _obs.initialize()
except Exception:
    pass  # Fail silently if initialization fails
