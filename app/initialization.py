#!/usr/bin/env python3
"""
APP INITIALIZATION — Load and sync authoritative metadata registry

This module runs ONCE when the app starts:
1. Loads the authoritative NYC Open Data registry
2. Syncs with Socrata API (if needed)
3. Updates any changed metadata
4. Makes registry available to entire app

Usage:
  # Call this FIRST in your app startup sequence
  from app.initialization import initialize_app

  initialize_app()  # Loads and syncs registry
"""

import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.data.nyc_open_data_registry import NYCDataRegistry

logger = logging.getLogger(__name__)

# Global registry instance
_REGISTRY = None

def initialize_app(auto_sync: bool = True) -> NYCDataRegistry:
    """
    Initialize app by loading the authoritative registry and (best-effort)
    syncing changed metadata from the source of truth.

    Resilience contract: the committed registry JSON is the permanent baseline.
    If the network sync fails (offline, Socrata down, timeout), the app still
    starts using the on-disk registry. Sync errors are logged, never raised.

    Args:
        auto_sync: If True, pull from the source of truth on init and update
            any changed metadata. Set False to load the on-disk baseline only.

    Returns:
        NYCDataRegistry instance (also stored globally)
    """
    global _REGISTRY

    logger.info("APP INITIALIZATION: Loading NYC Open Data Registry")

    # Step 1: Always load the on-disk baseline first (no network). This
    # guarantees the app has accurate metadata even if sync later fails.
    _REGISTRY = NYCDataRegistry(auto_sync=False)
    baseline_count = _REGISTRY.registry["metadata"]["total_datasets"]
    logger.info(f"Loaded registry baseline: {baseline_count} datasets")

    # Step 2: Best-effort sync of changed metadata from the source of truth.
    if auto_sync and _REGISTRY._should_sync():
        try:
            logger.info("Syncing changed metadata from source of truth...")
            _REGISTRY.sync()
            logger.info("Registry sync complete")
        except Exception as e:
            logger.warning(
                f"Registry sync failed ({e}); continuing with on-disk baseline "
                f"({baseline_count} datasets). Accuracy preserved from last sync."
            )

    meta = _REGISTRY.registry["metadata"]
    logger.info(
        f"Registry ready: {meta['total_datasets']} datasets, "
        f"{len(_REGISTRY.registry['index']['by_agency'])} agencies, "
        f"last synced {meta['last_synced']}"
    )
    return _REGISTRY

def get_registry() -> NYCDataRegistry:
    """Get the global registry instance."""
    if _REGISTRY is None:
        raise RuntimeError("Registry not initialized. Call initialize_app() first.")
    return _REGISTRY

def sync_registry() -> None:
    """Manually sync registry with Socrata API."""
    if _REGISTRY is None:
        raise RuntimeError("Registry not initialized. Call initialize_app() first.")
    logger.info("Manual registry sync requested...")
    _REGISTRY.sync()
    logger.info("Registry sync complete")

# Example usage in Dash app
def example_dash_integration():
    """
    Example: How to integrate into Dash app initialization

    Add this to your app/dash_app.py:

        from app.initialization import initialize_app, get_registry

        # Initialize on app load (runs ONCE)
        registry = initialize_app()

        # Later in callbacks, access registry
        def my_callback():
            registry = get_registry()
            dot_datasets = registry.filter_by_agency("DOT")
            # Use dot_datasets...
    """
    pass
