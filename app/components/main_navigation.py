"""
Main Navigation System: 4-view Role-Based Dashboard Router

Implements a sidebar navigation component for switching between 4 role-based views:
  1. Executive Summary — Leadership dashboards (7 headline Metrics)
  2. Operations — Daily ops monitoring (15 Metrics: inspection+violation+contractor)
  3. Analyst Tools — Deep analysis & work order assignment (8 dashboards + tools)
  4. Data — Quality & governance (data health, geographic, schema drift)

Architecture:
  - Collapsible dark sidebar with icon + label nav items
  - Active view highlighted with accent color
  - Mobile responsive (hamburger menu on <768px)
  - Smooth transitions between views
  - Integrated with dcc.Location for routing

Usage in dash_app.py:
    from app.components.main_navigation import render_main_navigation

    app.layout = dmc.MantineProvider(
        children=[
            dcc.Location(id="url", refresh=False),
            render_main_navigation(),
            # routing callback to update page content
        ]
    )

Integration with routing:
    After Task 11, the click handler will trigger location.pathname updates
    via dcc.Location, which feeds into app/callbacks/navigation.py's routing engine.
"""

import logging
from typing import Any, Dict, List

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, callback, dcc, html
from dash_iconify import DashIconify

logger = logging.getLogger(__name__)

# ==========================================
# --- NAVIGATION DATA & STRUCTURE ---
# ==========================================


def get_navigation_items() -> List[Dict[str, Any]]:
    """
    Returns structured navigation items for 4-view dashboard.

    Each item defines:
      - id: Unique nav item identifier (for callbacks)
      - label: Display label
      - view: View type identifier (executive|operations|analyst|data)
      - route: URL pathname
      - icon: mdi icon name
      - description: Tooltip/aria-label text
      - color: Accent color for active state (Mantine color)
      - badge: Optional badge ("beta", "new", etc.)

    Returns:
        List[Dict[str, Any]]: Navigation structure ready for rendering
    """
    return [
        {
            "id": "nav-executive",
            "label": "Executive Summary",
            "view": "executive",
            "route": "/views/executive",
            "icon": "mdi:chart-line",
            "description": "Leadership overview - 7 headline Metrics",
            "color": "blue",
            "badge": None,
        },
        {
            "id": "nav-operations",
            "label": "Operations",
            "view": "operations",
            "route": "/views/operations",
            "icon": "mdi:factory",
            "description": "Daily ops monitoring - 15 Metrics (inspection+violation+contractor)",
            "color": "orange",
            "badge": None,
        },
        {
            "id": "nav-analyst",
            "label": "Analyst Tools",
            "view": "analyst",
            "route": "/views/analyst",
            "icon": "mdi:chart-box-multiple",
            "description": "Deep analysis - 8 dashboards + conflict triage + export",
            "color": "cyan",
            "badge": "new",
        },
        {
            "id": "nav-data",
            "label": "Data",
            "view": "data",
            "route": "/views/data",
            "icon": "mdi:database-check",
            "description": "Quality & governance - data health, geographic, schema drift",
            "color": "grape",
            "badge": None,
        },
    ]


# ==========================================
# --- MAIN NAVIGATION COMPONENT ---
# ==========================================


def render_main_navigation() -> dmc.Stack:
    """
    Render the primary 4-view navigation sidebar with integrated routing.

    Returns a responsive navigation component that:
      - Displays 4 primary nav items (Executive, Operations, Analyst, Data)
      - Highlights active view based on current pathname
      - Collapses/expands on mobile (<768px)
      - Routes to /views/{view} on click
      - Includes visual badges for new/beta features

    Structure:
      dmc.Stack
        ├─ nav_header (branding + collapse button)
        ├─ nav_divider
        ├─ nav_items × 4 (Executive, Operations, Analyst, Data)
        └─ nav_footer (version info, help link)

    Returns:
        dmc.Stack: Complete sidebar navigation component
    """
    nav_items = get_navigation_items()

    # Build individual nav link buttons
    nav_buttons = [
        _render_nav_button(item)
        for item in nav_items
    ]

    return dmc.Stack(
        id="main-navigation",
        children=[
            dmc.ScrollArea(
                children=[
                    dmc.Stack(
                        p="md",
                        gap="xs",
                        children=[
                            # Header
                            _render_nav_header(),
                            dmc.Divider(),

                            # Navigation Buttons (4 primary views)
                            *nav_buttons,

                            # Footer
                            dmc.Divider(mt="md"),
                            _render_nav_footer(),
                        ],
                    )
                ],
                type="auto",
                style={"flex": 1},
            ),
        ],
        gap=0,
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
    )


def _render_nav_header() -> dmc.Group:
    """
    Render navigation header with branding and collapse toggle.

    Displays:
      - Icon + "Mission Control" title
      - Collapse button (mobile only)

    Returns:
        dmc.Group: Header component
    """
    return dmc.Group(
        children=[
            dmc.Group(
                children=[
                    DashIconify(
                        icon="mdi:radar",
                        width=28,
                        color="#0066CC",
                        style={"fontWeight": "bold"},
                    ),
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text(
                                "Mission Control",
                                size="md",
                                fw=900,
                                c="black",
                            ),
                            dmc.Text(
                                "4-View Dashboard",
                                size="xs",
                                c="gray",
                                fw=600,
                            ),
                        ],
                    ),
                ],
                gap="sm",
                style={"flex": 1},
            ),
        ],
        justify="space-between",
        mb="md",
    )


def _render_nav_button(item: Dict[str, Any]) -> html.Div:
    """
    Render a single navigation button for a view.

    Each button:
      - Displays icon + label + optional badge
      - Highlighted when active (by pathname match)
      - Routes to item['route'] on click
      - Shows tooltip with description

    Args:
        item: Navigation item dict with keys: id, label, view, route, icon, etc.

    Returns:
        html.Div: Navigation button with badge and active state styling
    """
    badge_element = None
    if item.get("badge"):
        badge_element = dmc.Badge(
            item["badge"].upper(),
            color="red",
            variant="filled",
            size="xs",
            ml="auto",
        )

    return dmc.Paper(
        id=f"{item['id']}-container",
        withBorder=False,
        p="md",
        radius="md",
        className="nav-item",
        style={
            "cursor": "pointer",
            "transition": "all 0.2s ease",
            "border": "2px solid transparent",
            "backgroundColor": "#F8F9FA",
        },
        children=[
            dmc.Anchor(
                href=item["route"],
                id=item["id"],
                style={"textDecoration": "none"},
                anchorProps={"title": item["description"]},
                children=[
                    dmc.Group(
                        children=[
                            DashIconify(
                                icon=item["icon"],
                                width=24,
                                color="#0066CC",
                            ),
                            dmc.Stack(
                                gap=2,
                                children=[
                                    dmc.Text(
                                        item["label"],
                                        size="sm",
                                        fw=700,
                                        c="black",
                                    ),
                                    dmc.Text(
                                        item["description"],
                                        size="xs",
                                        c="gray",
                                        fw=400,
                                    ),
                                ],
                                style={"flex": 1},
                            ),
                            badge_element if badge_element else None,
                        ],
                        gap="md",
                        align="center",
                        style={"width": "100%"},
                    )
                ],
                **{"aria-label": f"Navigate to {item['label']}"},
            )
        ],
        mb="sm",
    )


def _render_nav_footer() -> dmc.Stack:
    """
    Render navigation footer with version info and help link.

    Displays:
      - Version badge (v1.0-beta)
      - Help/docs link
      - Settings access

    Returns:
        dmc.Stack: Footer component
    """
    return dmc.Stack(
        gap="sm",
        children=[
            dmc.Group(
                children=[
                    DashIconify(icon="mdi:information-outline", width=16),
                    dmc.Text(
                        "Mission Control v1.0-beta",
                        size="xs",
                        c="dimmed",
                    ),
                ],
                gap="xs",
            ),
            dmc.Divider(),
            dmc.Group(
                children=[
                    dmc.Anchor(
                        "Documentation",
                        href="/tutorials",
                        size="xs",
                        c="blue",
                    ),
                    dmc.Text("|", size="xs", c="gray"),
                    dmc.Anchor(
                        "Settings",
                        href="/settings",
                        size="xs",
                        c="blue",
                    ),
                ],
                gap="xs",
            ),
        ],
    )


# ==========================================
# --- RESPONSIVE MOBILE NAVIGATION ---
# ==========================================


def render_mobile_navigation_trigger() -> dmc.ActionIcon:
    """
    Render mobile hamburger menu trigger (visible on <768px).

    Returns:
        dmc.ActionIcon: Hamburger icon button to toggle sidebar
    """
    return dmc.ActionIcon(
        DashIconify(icon="mdi:menu"),
        id="nav-mobile-trigger",
        variant="subtle",
        color="dark",
        size="lg",
        className="nav-mobile-only",
        style={"display": "none"},
        **{"aria-label": "Toggle navigation menu"},
    )


# ==========================================
# --- CALLBACKS: NAVIGATION STATE ---
# ==========================================


def register_navigation_callbacks(app):
    """
    Register Dash callbacks for 4-view navigation system.

    Manages:
      1. Active view highlighting (matches pathname to nav item)
      2. Mobile sidebar toggle (collapse on small screens)
      3. Navigation item routing (href-based)
      4. View-specific content loading (integration with routing engine)

    Args:
        app: Dash application instance
    """

    @app.callback(
        [
            Output(f"{item['id']}-container", "style")
            for item in get_navigation_items()
        ],
        Input("url", "pathname"),
    )
    def update_nav_active_styles(pathname):
        """
        Update navigation item styles to highlight active view.

        Matches current pathname against route definitions and applies
        active styling (border + background color) to matching nav item.

        Args:
            pathname: Current URL pathname from dcc.Location

        Returns:
            List[Dict]: Style dicts for each nav item (active/inactive)
        """
        nav_items = get_navigation_items()
        styles = []

        for item in nav_items:
            is_active = pathname.startswith(item["route"])

            if is_active:
                # Active state: highlight border + background
                styles.append({
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "border": f"2px solid #0066CC",
                    "backgroundColor": "#E7F5FF",
                })
            else:
                # Inactive state: default styling
                styles.append({
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "border": "2px solid transparent",
                    "backgroundColor": "#F8F9FA",
                })

        return styles

    @app.callback(
        Output("nav-mobile-trigger", "style"),
        Input("url", "pathname"),
        prevent_initial_call=True,
    )
    def toggle_mobile_nav_visibility(pathname):
        """
        Show/hide mobile hamburger menu (for responsive design).

        On screens <768px, displays hamburger. On larger screens, hides.
        (CSS media query handles actual display; this ensures Dash-side sync.)

        Args:
            pathname: Current pathname (unused, triggers on navigation)

        Returns:
            Dict: Style dict with display property
        """
        # CSS media query will override this; here we default to show
        # (mobile logic is in CSS class .nav-mobile-only)
        return {"display": "block"}


# ==========================================
# --- STYLING: CSS CLASSES FOR NAVIGATION ---
# ==========================================

def get_navigation_css() -> str:
    """
    Return inline CSS for navigation responsive design.

    Handles:
      - Mobile hamburger menu (display on <768px)
      - Sidebar collapse animation
      - Active state styling
      - Touch-friendly hit targets
      - Dark mode support (placeholder for future theming)

    Returns:
        str: CSS rules for navigation component
    """
    return """
    /* Main Navigation Container */
    #main-navigation {
        height: 100%;
        background: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }

    /* Navigation Items */
    .nav-item {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .nav-item:hover {
        background-color: #E7F5FF;
        border-color: #0066CC;
        transform: translateX(4px);
    }

    .nav-item a {
        text-decoration: none;
        color: inherit;
    }

    /* Mobile Navigation */
    @media (max-width: 768px) {
        .nav-mobile-only {
            display: block !important;
        }

        #main-navigation {
            position: fixed;
            left: 0;
            top: 70px;
            width: 300px;
            height: calc(100vh - 70px);
            z-index: 100;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
        }

        #main-navigation.open {
            transform: translateX(0);
        }

        /* Sidebar backdrop on mobile */
        #nav-backdrop {
            position: fixed;
            top: 70px;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            z-index: 99;
        }

        #nav-backdrop.open {
            display: block;
        }
    }

    /* Dark theme support (future) */
    @media (prefers-color-scheme: dark) {
        #main-navigation {
            background: #1A1A1A;
            border-right-color: #333333;
        }

        .nav-item {
            background-color: #2C2C2C;
        }

        .nav-item:hover {
            background-color: #0066CC;
            color: white;
        }
    }

    /* Accessibility: Focus states */
    .nav-item a:focus {
        outline: 2px solid #0066CC;
        outline-offset: 2px;
    }

    /* Touch targets */
    @media (pointer: coarse) {
        .nav-item {
            min-height: 56px;
            display: flex;
            align-items: center;
        }
    }
    """


# ==========================================
# --- NAVIGATION STATE STORE ---
# ==========================================


def render_navigation_store() -> dcc.Store:
    """
    Render dcc.Store component for persisting navigation state.

    Stores:
      - current_view: Active view type (executive|operations|analyst|data)
      - sidebar_collapsed: Whether sidebar is collapsed on mobile

    Returns:
        dcc.Store: Session-based store for nav state
    """
    return dcc.Store(
        id="store-navigation-state",
        data={
            "current_view": "executive",
            "sidebar_collapsed": False,
        },
        storage_type="session",
    )
