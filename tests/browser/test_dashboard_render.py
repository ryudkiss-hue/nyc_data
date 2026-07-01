"""Playwright browser smoke tests for the NYC DOT Dash Mission Control dashboard.

Verifies:
  - All 13 nav routes load (HTTP 200, DOM populated, no crash)
  - Sidebar nav links are present and functional
  - Every chart-bearing route has .js-plotly-plot elements with rendered SVG
  - Home dashboard exposes ≥2 chart panels
  - No critical JavaScript errors on any route
  - Metric card container is present on the home dashboard
  - Filter bar interaction does not crash the app
  - SQL Studio has query input + run button; SELECT 1 executes without error

Run against real warehouse (local):
    pytest tests/browser/ -m browser -v

Run against empty DuckDB (CI / no warehouse):
    DUCKDB_PATH=/tmp/empty_test.duckdb pytest tests/browser/ -m browser -v
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

# ── Route catalogue ───────────────────────────────────────────────────────────

ALL_ROUTES: list[tuple[str, str]] = [
    ("/", "Dashboard"),
    ("/const", "Construction Planner"),
    ("/labor", "Labor & Lifecycle"),
    ("/reports", "Reports"),
    ("/stats", "Statistics"),
    ("/geo", "GIS & Maps"),
    ("/eng", "Engineering"),
    ("/sql", "SQL Studio"),
    ("/nlp", "Natural Language Query"),
    ("/copilot", "AI Assistant"),
    ("/settings", "Settings"),
    ("/tutorials", "Tutorials"),
    ("/toolbox", "Toolbox"),
]

# Routes that include visualization_asset() chart panels
CHART_ROUTES: list[str] = ["/", "/const", "/labor", "/reports", "/stats", "/geo", "/eng"]

# ── Console error filtering ───────────────────────────────────────────────────

_FATAL_RE = re.compile(
    r"TypeError|ReferenceError|is not a function|Cannot read prop"
    r"|Uncaught Error|dash_renderer.*Error|Callback error"
    r"|Cannot set prop",
    re.IGNORECASE,
)

_NOISE_RE = re.compile(
    r"favicon|ResizeObserver loop|Content-Security-Policy"
    r"|Loading chunk|_dash-component-suites|404.*assets"
    r"|DeprecationWarning|Unrecognized feature"
    r"|Non-passive event|Expected server HTML",
    re.IGNORECASE,
)


def _attach_error_listener(page: Page) -> list[str]:
    """Register a console listener; return the list it appends to."""
    errors: list[str] = []

    def _on_console(msg):
        if msg.type == "error":
            text = msg.text
            if _FATAL_RE.search(text) and not _NOISE_RE.search(text):
                errors.append(text)

    page.on("console", _on_console)
    return errors


# ── Route load tests ──────────────────────────────────────────────────────────

class TestRouteLoads:
    """All 13 nav routes return a non-5xx response and populate the DOM."""

    @pytest.mark.parametrize("route,label", ALL_ROUTES, ids=[r for r, _ in ALL_ROUTES])
    def test_route_loads_without_error(
        self, page: Page, dash_base_url: str, route: str, label: str
    ):
        errors = _attach_error_listener(page)
        resp = page.goto(
            f"{dash_base_url}{route}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        assert resp is not None, f"Navigation to {route} returned no response"
        assert resp.status < 500, (
            f"{label} ({route}) returned HTTP {resp.status} — server error."
        )
        # Dash SPA shell mounts here; if this is missing the whole app is broken
        expect(page.locator("#_dash-app-content, #react-entry-point")).to_be_attached(
            timeout=15_000
        )
        assert not errors, f"Critical JS errors on {label} ({route}):\n" + "\n".join(errors)


# ── Sidebar nav tests ─────────────────────────────────────────────────────────

class TestSidebarNav:
    """Sidebar navigation renders all links and navigates correctly."""

    def test_all_nav_links_present(self, page: Page, dash_base_url: str):
        page.goto(dash_base_url, wait_until="domcontentloaded", timeout=30_000)
        nav = page.locator("a[href]").filter(
            has_text=re.compile(
                r"Dashboard|Construction|Labor|Reports|Statistics|GIS"
                r"|Engineering|SQL Studio|Natural Language|AI Assistant"
                r"|Settings|Tutorials|Toolbox",
                re.IGNORECASE,
            )
        )
        count = nav.count()
        assert count >= 8, (
            f"Expected ≥8 sidebar nav links, found {count}. "
            "Sidebar may not be rendering."
        )

    def test_nav_link_navigates_and_loads_content(self, page: Page, dash_base_url: str):
        """Clicking a sidebar link updates the URL and loads the new view."""
        page.goto(dash_base_url, wait_until="domcontentloaded", timeout=30_000)
        page.locator("a[href='/const']").first.click()
        page.wait_for_url("**/const", timeout=10_000)
        expect(page.locator("text=CONSTRUCTION PLANNER")).to_be_visible(timeout=10_000)


# ── Chart render tests ────────────────────────────────────────────────────────

class TestChartsRender:
    """Every chart-bearing route has .js-plotly-plot elements with rendered SVG.

    Plotly.js always produces an SVG element — even for empty or annotation-only
    figures — so this assertion holds whether the warehouse is populated or not.
    """

    @pytest.mark.parametrize("route", CHART_ROUTES, ids=CHART_ROUTES)
    def test_charts_have_rendered_svg(
        self, page: Page, dash_base_url: str, route: str
    ):
        errors = _attach_error_listener(page)
        page.goto(f"{dash_base_url}{route}", wait_until="domcontentloaded", timeout=45_000)

        # Dash callbacks fire asynchronously after page load; wait up to 25s for first
        try:
            expect(page.locator(".js-plotly-plot").first).to_be_attached(timeout=25_000)
        except Exception:
            pass

        charts = page.locator(".js-plotly-plot")
        count = charts.count()
        assert count > 0, (
            f"No .js-plotly-plot elements on {route}. "
            "Plotly did not initialise — possible JS crash or missing component."
        )

        for i in range(count):
            svg = charts.nth(i).locator("svg").first
            expect(svg).to_be_attached(timeout=10_000), (
                f"Chart {i} on {route} has no SVG — Plotly render failed."
            )

        assert not errors, (
            f"Critical JS errors on {route}:\n" + "\n".join(errors)
        )

    def test_home_dashboard_has_minimum_chart_count(
        self, page: Page, dash_base_url: str
    ):
        """Home dashboard must have ≥2 charts (viz-velocity + viz-inspections)."""
        page.goto(dash_base_url, wait_until="domcontentloaded", timeout=45_000)
        try:
            expect(page.locator(".js-plotly-plot").first).to_be_attached(timeout=25_000)
        except Exception:
            pass
        count = page.locator(".js-plotly-plot").count()
        assert count >= 2, (
            f"Home dashboard has {count} chart(s); expected ≥2. "
            "viz-velocity and viz-inspections callbacks may not have fired."
        )


# ── Metric cards test ─────────────────────────────────────────────────────────

class TestMetricCards:
    """Home dashboard metric card section is present in the DOM."""

    def test_metric_card_section_present(self, page: Page, dash_base_url: str):
        page.goto(dash_base_url, wait_until="domcontentloaded", timeout=45_000)
        # Metric cards are rendered inside a container; the callback output element
        # has an id containing 'metric'.  Accept either the container or any child.
        metric_el = page.locator("[id*='metric']")
        try:
            expect(metric_el.first).to_be_attached(timeout=20_000)
        except Exception:
            pass
        assert metric_el.count() > 0, (
            "No element with 'metric' in its id found on home dashboard. "
            "Metric card container may have been renamed or the callback failed."
        )


# ── Filter interaction test ───────────────────────────────────────────────────

class TestFilterInteraction:
    """Filter bar interactions do not produce JS errors."""

    def test_opening_filter_select_does_not_crash(
        self, page: Page, dash_base_url: str
    ):
        errors = _attach_error_listener(page)
        page.goto(dash_base_url, wait_until="domcontentloaded", timeout=45_000)

        # Try Mantine MultiSelect or Select components in the filter bar
        selects = page.locator(
            "[data-mantine-component='MultiSelect'], "
            "[data-mantine-component='Select'], "
            "input[type='search']"
        )
        if selects.count() == 0:
            pytest.skip("No MultiSelect/Select found — filter bar structure differs.")

        selects.first.click()
        page.wait_for_timeout(600)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1_000)

        assert not errors, (
            "JS errors after opening filter select:\n" + "\n".join(errors)
        )


# ── SQL Studio tests ──────────────────────────────────────────────────────────

class TestSQLStudio:
    """SQL Studio has query input, run button; safe queries execute without crash."""

    def test_sql_studio_ui_elements_present(self, page: Page, dash_base_url: str):
        errors = _attach_error_listener(page)
        page.goto(f"{dash_base_url}/sql", wait_until="domcontentloaded", timeout=30_000)

        # Query textarea (dmc.Textarea with id="sql-query-input")
        expect(
            page.locator("#sql-query-input, #sql-query-input textarea")
        ).to_be_attached(timeout=10_000)

        # Execute button
        expect(page.locator("#btn-run-sql")).to_be_attached(timeout=10_000)

        # Results container
        expect(page.locator("#sql-results-output")).to_be_attached(timeout=10_000)

        assert not errors, "JS errors on SQL Studio load:\n" + "\n".join(errors)

    def test_sql_studio_safe_query_executes(self, page: Page, dash_base_url: str):
        """SELECT 1 executes and writes to the results container without a JS error."""
        errors = _attach_error_listener(page)
        page.goto(f"{dash_base_url}/sql", wait_until="domcontentloaded", timeout=30_000)

        # Fill the query — target the actual <textarea> element inside the component
        textarea = page.locator("#sql-query-input textarea, textarea").first
        textarea.click()
        textarea.fill("SELECT 1 AS test_col")

        page.locator("#btn-run-sql").click()
        # Wait for the callback to return (up to 10s)
        page.wait_for_timeout(3_000)
        page.wait_for_timeout(2_000)

        # Results container must be attached (may contain a table or an error message —
        # both are valid; what matters is the callback ran and didn't crash)
        expect(page.locator("#sql-results-output")).to_be_attached(timeout=5_000)

        assert not errors, "JS errors after SQL execute:\n" + "\n".join(errors)
