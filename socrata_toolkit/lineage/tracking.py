"""Integration decorators and context managers for automatic lineage tracking.

This module provides decorators and context managers to automatically track
data transformations without requiring explicit lineage registration code.
Integrates with pipeline.py, validation, schema_registry, and persistence layers.

Example:
    @track_transformation(
        inputs=['construction_list_raw'],
        outputs=['construction_list_staging']
    )
    def clean_construction_data(df):
        return df.dropna()
    
    with lineage_context('aggregate_by_borough', inputs, outputs):
        result = aggregate_function()
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .core import (
    TransformationNode,
    ExecutionRecord,
    NodeType,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)

# Global lineage context
_lineage_context: Optional[Dict[str, Any]] = None
_lineage_nodes: Dict[str, TransformationNode] = {}
_lineage_persistence: Optional[Any] = None


def set_global_persistence(persistence: Any) -> None:
    """Set global lineage persistence instance.
    
    Args:
        persistence: LineagePersistence instance
    """
    global _lineage_persistence
    _lineage_persistence = persistence
    logger.info("Set global lineage persistence")


def track_transformation(
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    transformation_type: str = "transformation",
    owner: str = "system",
    tags: Optional[List[str]] = None,
) -> Callable:
    """Decorator to automatically track transformation execution.
    
    Records execution metrics including row counts, duration, and errors.
    Integrates with persistent lineage store if available.
    
    Args:
        inputs: List of input dataset node IDs
        outputs: List of output dataset node IDs
        transformation_type: Node type (transformation, aggregation, etc.)
        owner: Owner email or user ID
        tags: Optional metadata tags
        
    Returns:
        Decorated function that auto-tracks execution
        
    Example:
        @track_transformation(
            inputs=['raw_construction_list'],
            outputs=['clean_construction_list'],
            owner='data-eng@nyc.gov'
        )
        def clean_data(df):
            return df.dropna()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create or get node
            node_id = f"{func.__module__}.{func.__name__}"
            node = _lineage_nodes.get(node_id)
            
            if not node:
                node = TransformationNode(
                    node_id=node_id,
                    name=func.__name__,
                    node_type=NodeType(transformation_type),
                    description=func.__doc__ or f"Transformation: {func.__name__}",
                    owner=owner,
                    input_datasets=inputs or [],
                    output_datasets=outputs or [],
                    tags=tags or [],
                    configuration={"function": func.__name__, "module": func.__module__},
                )
                _lineage_nodes[node_id] = node
                
                # Save to persistence if available
                if _lineage_persistence:
                    try:
                        _lineage_persistence.save_node(node)
                    except Exception as e:
                        logger.warning(f"Failed to save lineage node: {e}")

            # Track execution
            start_time = time.time()
            start_dt = datetime.now(timezone.utc)
            error_msg = None
            input_rows = 0
            output_rows = 0

            try:
                result = func(*args, **kwargs)
                
                # Try to count rows from result
                try:
                    if hasattr(result, '__len__'):
                        output_rows = len(result)
                    elif hasattr(result, 'shape'):  # pandas DataFrame
                        output_rows = result.shape[0]
                except Exception:
                    pass

                status = ExecutionStatus.SUCCESS
                return result

            except Exception as e:
                error_msg = str(e)
                status = ExecutionStatus.FAILED
                logger.error(f"Transformation {func.__name__} failed: {e}")
                raise

            finally:
                duration = time.time() - start_time
                
                # Record execution
                try:
                    exec_record = ExecutionRecord(
                        node_id=node_id,
                        started_at=start_dt,
                        completed_at=datetime.now(timezone.utc),
                        duration_seconds=duration,
                        status=status,
                        input_row_count=input_rows,
                        output_row_count=output_rows,
                        error_message=error_msg,
                    )
                    node.record_execution(
                        status=status,
                        input_rows=input_rows,
                        output_rows=output_rows,
                        duration_secs=duration,
                        error_msg=error_msg,
                    )
                    
                    # Save execution to persistence
                    if _lineage_persistence:
                        try:
                            _lineage_persistence.save_execution(exec_record)
                        except Exception as e:
                            logger.warning(f"Failed to save execution record: {e}")
                except Exception as e:
                    logger.error(f"Failed to record execution: {e}")

        return wrapper
    return decorator


@contextmanager
def lineage_context(
    context_name: str,
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    owner: str = "system",
    tags: Optional[List[str]] = None,
):
    """Context manager for tracking transformations in code blocks.
    
    Records execution of code within the context, tracking row counts and timing.
    
    Args:
        context_name: Name for this transformation context
        inputs: List of input dataset node IDs
        outputs: List of output dataset node IDs
        owner: Owner email or user ID
        tags: Optional metadata tags
        
    Yields:
        Dictionary with tracking info
        
    Example:
        with lineage_context('daily_aggregation', inputs=['raw'], outputs=['aggregated']):
            result = heavy_computation()
    """
    node_id = f"context.{context_name}"
    node = TransformationNode(
        node_id=node_id,
        name=context_name,
        node_type=NodeType.TRANSFORMATION,
        description=f"Code block: {context_name}",
        owner=owner,
        input_datasets=inputs or [],
        output_datasets=outputs or [],
        tags=tags or [],
    )
    
    if _lineage_persistence:
        try:
            _lineage_persistence.save_node(node)
        except Exception as e:
            logger.warning(f"Failed to save context node: {e}")
    
    start_time = time.time()
    start_dt = datetime.now(timezone.utc)
    error_msg = None
    status = ExecutionStatus.SUCCESS
    
    tracking_info = {
        "node_id": node_id,
        "start_time": start_dt,
        "context_name": context_name,
    }
    
    try:
        yield tracking_info
    except Exception as e:
        error_msg = str(e)
        status = ExecutionStatus.FAILED
        logger.error(f"Context {context_name} failed: {e}")
        raise
    finally:
        duration = time.time() - start_time
        
        try:
            exec_record = ExecutionRecord(
                node_id=node_id,
                started_at=start_dt,
                completed_at=datetime.now(timezone.utc),
                duration_seconds=duration,
                status=status,
                error_message=error_msg,
            )
            
            if _lineage_persistence:
                try:
                    _lineage_persistence.save_execution(exec_record)
                except Exception as e:
                    logger.warning(f"Failed to save execution: {e}")
        except Exception as e:
            logger.error(f"Failed to record context execution: {e}")


def register_ingestion_node(
    dataset_id: str,
    dataset_name: str,
    source: str = "socrata",
    owner: str = "system",
    schema_version: Optional[str] = None,
) -> TransformationNode:
    """Register a data ingestion node.
    
    Called when data is first ingested from a source (Socrata, API, file, etc.).
    
    Args:
        dataset_id: Unique dataset identifier
        dataset_name: Human-readable dataset name
        source: Source system (socrata, api, file, etc.)
        owner: Data owner
        schema_version: Link to schema registry version
        
    Returns:
        TransformationNode for the ingestion
    """
    node_id = f"ingest.{dataset_id}"
    node = TransformationNode(
        node_id=node_id,
        name=f"{dataset_name} Ingestion",
        node_type=NodeType.INGESTION,
        description=f"Data ingestion from {source}",
        owner=owner,
        schema_version=schema_version,
        tags=["ingestion", source],
        configuration={"source": source, "dataset_id": dataset_id},
    )
    
    _lineage_nodes[node_id] = node
    
    if _lineage_persistence:
        try:
            _lineage_persistence.save_node(node)
        except Exception as e:
            logger.warning(f"Failed to save ingestion node: {e}")
    
    logger.info(f"Registered ingestion node {node_id}")
    return node


def register_sink_node(
    sink_id: str,
    sink_name: str,
    sink_type: str,
    input_datasets: List[str],
    owner: str = "system",
) -> TransformationNode:
    """Register a data sink (persistence target) node.
    
    Called when data is persisted to a target (database, warehouse, file, etc.).
    
    Args:
        sink_id: Unique sink identifier
        sink_name: Human-readable sink name
        sink_type: Target type (postgres, mongo, parquet, etc.)
        input_datasets: List of source dataset node IDs
        owner: Sink owner
        
    Returns:
        TransformationNode for the sink
    """
    node_id = f"sink.{sink_id}"
    node = TransformationNode(
        node_id=node_id,
        name=f"{sink_name} Sink",
        node_type=NodeType.SINK,
        description=f"Data persistence to {sink_type}",
        owner=owner,
        input_datasets=input_datasets,
        tags=["sink", sink_type],
        configuration={"sink_type": sink_type, "sink_id": sink_id},
    )
    
    _lineage_nodes[node_id] = node
    
    if _lineage_persistence:
        try:
            _lineage_persistence.save_node(node)
        except Exception as e:
            logger.warning(f"Failed to save sink node: {e}")
    
    logger.info(f"Registered sink node {node_id}")
    return node


def register_validation_node(
    validation_id: str,
    validation_name: str,
    input_dataset: str,
    rules: Optional[Dict[str, Any]] = None,
    owner: str = "system",
) -> TransformationNode:
    """Register a data quality validation node.
    
    Called when data quality checks are performed.
    
    Args:
        validation_id: Unique validation identifier
        validation_name: Human-readable validation name
        input_dataset: Dataset being validated
        rules: Validation rules and thresholds
        owner: Validation owner
        
    Returns:
        TransformationNode for the validation
    """
    node_id = f"validate.{validation_id}"
    node = TransformationNode(
        node_id=node_id,
        name=f"{validation_name} Validation",
        node_type=NodeType.VALIDATION,
        description=f"Data quality validation",
        owner=owner,
        input_datasets=[input_dataset],
        tags=["validation", "quality"],
        configuration={"validation_id": validation_id, "rules": rules or {}},
    )
    
    _lineage_nodes[node_id] = node
    
    if _lineage_persistence:
        try:
            _lineage_persistence.save_node(node)
        except Exception as e:
            logger.warning(f"Failed to save validation node: {e}")
    
    logger.info(f"Registered validation node {node_id}")
    return node


def get_tracked_node(node_id: str) -> Optional[TransformationNode]:
    """Get a tracked lineage node by ID."""
    return _lineage_nodes.get(node_id)


def get_all_tracked_nodes() -> Dict[str, TransformationNode]:
    """Get all tracked lineage nodes."""
    return _lineage_nodes.copy()
