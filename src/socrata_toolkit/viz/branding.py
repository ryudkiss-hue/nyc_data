"""NYC DOT Industrial Branding & Style Constants.

Enforces #FFFFFF background, #000000 text, and #228BE6 (blue) accents.
Provides consistent color palettes for both Matplotlib and Plotly.
"""

# Core Branding Colors
DOT_BLUE = "#228BE6"   # Primary Accent / DOT Blue
DOT_BLACK = "#000000"  # Primary Text
DOT_WHITE = "#FFFFFF"  # Background
DOT_GRAY = "#6C757D"   # Secondary / De-emphasized

# WCAG 2.1 AA Compliant Palette (Accessible combinations)
# High contrast, distinct for color-blind users
WCAG_PALETTE = [
    DOT_BLUE,
    "#D63384", # Deep Pink
    "#198754", # Success Green (Dark)
    "#FD7E14", # Warning Orange (High Contrast)
    "#6610F2", # Indigo
    "#20C997", # Teal
    "#E67E22", # Carrot
]

# Borough-specific colors (Consistent across charts)
BOROUGH_COLORS = {
    "MANHATTAN": DOT_BLUE,
    "BRONX": "#6610F2",
    "BROOKLYN": "#D63384",
    "QUEENS": "#198754",
    "STATEN ISLAND": "#FD7E14",
}

# Status colors
STATUS_COLORS = {
    "complete": "#198754",
    "Complete": "#198754",
    "in_progress": "#E67E22",
    "In Progress": "#E67E22",
    "delayed": "#DC3545",
    "not_started": DOT_GRAY,
    "Active": DOT_BLUE,
    "Pending Repair": "#FD7E14",
    "Cancelled": "#DC3545",
    "City-Initiated": DOT_BLUE,
}

# Matplotlib Style Override
MATPLOTLIB_STYLE = {
    "axes.facecolor": DOT_WHITE,
    "axes.edgecolor": DOT_BLACK,
    "axes.labelcolor": DOT_BLACK,
    "xtick.color": DOT_BLACK,
    "ytick.color": DOT_BLACK,
    "text.color": DOT_BLACK,
    "figure.facecolor": DOT_WHITE,
    "grid.color": "#E9ECEF",
    "axes.prop_cycle": f"cycler('color', {WCAG_PALETTE})",
}

# Plotly Layout Override
PLOTLY_LAYOUT = {
    "paper_bgcolor": DOT_WHITE,
    "plot_bgcolor": DOT_WHITE,
    "font": {"color": DOT_BLACK},
    "colorway": WCAG_PALETTE,
}
