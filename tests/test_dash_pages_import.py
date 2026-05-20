"""Import all Dash pages to catch syntax and registration errors."""

from __future__ import annotations

import importlib
import os

import pytest

# Dash pages call register_page at import time; app must exist first.
import dash_app.app  # noqa: F401

from dash import page_registry

CORE_PAGE_MODULES = [
    "dash_app.pages.home",
    "dash_app.pages.explore",
    "dash_app.pages.construction",
    "dash_app.pages.contracts",
    "dash_app.pages.metrics",
    "dash_app.pages.inquiries",
    "dash_app.pages.review",
    "dash_app.pages.data_trust",
    "dash_app.pages.publish",
    "dash_app.pages.settings",
]

DEBUG_PAGE_MODULES = [
    "dash_app.pages.analytics",
    "dash_app.pages.quantum",
    "dash_app.pages.geospatial",
    "dash_app.pages.devtools",
]


@pytest.mark.parametrize("module_name", CORE_PAGE_MODULES)
def test_dash_core_page_imports(module_name: str):
    mod = importlib.import_module(module_name)
    assert hasattr(mod, "layout")


def test_dash_app_imports():
    assert dash_app.app.app is not None


def test_core_pages_registered():
    registered = {p["module"] for p in page_registry.values()}
    for module_name in CORE_PAGE_MODULES:
        assert module_name in registered, f"{module_name} not in page_registry"


def test_dash_debug_pages_not_registered_by_default():
    """Debug/lab pages register only when NYC_DOT_DEBUG=1."""
    assert os.getenv("NYC_DOT_DEBUG", "") not in ("1", "true", "yes")
    registered = {p["module"] for p in page_registry.values()}
    for module_name in DEBUG_PAGE_MODULES:
        assert module_name not in registered, f"{module_name} should require NYC_DOT_DEBUG=1"
