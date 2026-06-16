import importlib.util
import sys
from unittest.mock import MagicMock

import pytest

# Stub heavy optional dependencies ONLY when they are not installed, so the
# callback modules can be imported without them. Never clobber a real module
# already present in sys.modules — doing so leaks MagicMock stand-ins into
# every test collected afterwards (e.g. the spatial suite), breaking real
# geometry/GeoDataFrame assertions.
for _mod in ("prophet", "geopandas", "shapely", "shapely.geometry"):
    if importlib.util.find_spec(_mod) is None and _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import dash
import pytest
from dash import Dash

from app.callbacks.analytics import register_analytics_callbacks
from app.callbacks.copilot import register_copilot_callbacks
from app.callbacks.export import register_export_callbacks
from app.callbacks.ingestion import register_ingestion_callbacks
from app.callbacks.navigation import register_navigation_callbacks


def test_callback_registration():
    """Verify that all modular callbacks are correctly registered to a Dash app."""
    app = Dash(__name__)
    dm_instance = MagicMock()

    # Registration calls
    register_navigation_callbacks(app)
    register_ingestion_callbacks(app, dm_instance)
    register_analytics_callbacks(app, dm_instance)
    register_export_callbacks(app, dm_instance)
    register_copilot_callbacks(app)

    # Inspect internal callback map (Dash 2.x+)
    assert len(app.callback_map) > 0

    # Helper to check for output in map
    def has_output(output_id):
        return any(output_id in k for k in app.callback_map.keys())

    # Verify specific callback existence
    assert has_output("mantine-provider.forceColorScheme")
    assert has_output("store-data-loaded.data")
    assert has_output("audit-results-container.children")
    assert has_output("download-manager.data")
    assert has_output("copilot-history.children")
