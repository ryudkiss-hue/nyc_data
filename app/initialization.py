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
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.data.nyc_open_data_registry import NYCDataRegistry

logger = logging.getLogger(__name__)

# Global registry instance
_REGISTRY = None

def initialize_app() -> NYCDataRegistry:
    """
    Initialize app by loading and syncing authoritative registry.

    Returns:
        NYCDataRegistry instance (also stored globally)
    """
    global _REGISTRY

    logger.info("=" * 80)
    logger.info("APP INITIALIZATION: Loading NYC Open Data Registry")
    logger.info("=" * 80)

    try:
        # Create registry (will auto-sync if needed)
        _REGISTRY = NYCDataRegistry(auto_sync=True)

        logger.info("=" * 80)
        logger.info("REGISTRY STATUS")
        logger.info("=" * 80)
        logger.info(f"Total datasets loaded: {_REGISTRY.registry['metadata']['total_datasets']}")
        logger.info(f"Last synced: {_REGISTRY.registry['metadata']['last_synced']}")
        logger.info(f"Agencies: {len(_REGISTRY.registry['index']['by_agency'])}")
        logger.info(f"Keywords indexed: {len(_REGISTRY.registry['index']['by_keywords'])}")
        logger.info("=" * 80)
        logger.info("App ready: Use get_registry() to access metadata")
        logger.info("=" * 80)

        return _REGISTRY

    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize registry: {e}")
        raise

def get_registry() -> NYCDataRegistry:
    """Get the global registry instance."""
    global _REGISTRY
    if _REGISTRY is None:
        raise RuntimeError("Registry not initialized. Call initialize_app() first.")
    return _REGISTRY

def sync_registry() -> None:
    """Manually sync registry with Socrata API."""
    global _REGISTRY
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
