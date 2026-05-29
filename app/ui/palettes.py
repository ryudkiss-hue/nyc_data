"""Color-blind-safe palettes for Manhattan Mission Control.

All categorical palettes are distinguishable under deuteranopia, protanopia,
and tritanopia. Sequential/diverging scales are perceptually uniform.

References:
  - Okabe & Ito (2008), "Color Universal Design"
  - Viridis (Smith & van der Walt, 2015) — perceptually uniform
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Categorical — Okabe-Ito (8 colors, color-blind safe)
# ---------------------------------------------------------------------------
OKABE_ITO: list[str] = [
    "#56B4E9",  # sky blue
    "#E69F00",  # orange
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#999999",  # grey
]

# Agency-tuned categorical (brand-forward but still CB-distinguishable)
AGENCY_CATEGORICAL: list[str] = [
    "#3B82F6",  # blue
    "#F4C430",  # agency gold
    "#10B981",  # green
    "#EF4444",  # red
    "#A78BFA",  # violet
    "#F59E0B",  # amber
    "#06B6D4",  # cyan
    "#EC4899",  # pink
]

# ---------------------------------------------------------------------------
# Sequential — viridis sampled (perceptually uniform)
# ---------------------------------------------------------------------------
VIRIDIS: list[str] = [
    "#440154", "#46327e", "#365c8d", "#277f8e",
    "#1fa187", "#4ac16d", "#a0da39", "#fde725",
]

# Cividis — viridis variant optimized for color-vision deficiency
CIVIDIS: list[str] = [
    "#00204d", "#23396d", "#575d6d", "#7b7a77",
    "#a59c74", "#d3c164", "#ffe945",
]

# ---------------------------------------------------------------------------
# Semantic — status / severity (paired with icons, never color-alone)
# ---------------------------------------------------------------------------
SEMANTIC = {
    "critical": "#EF4444",
    "warn": "#F59E0B",
    "ok": "#10B981",
    "info": "#3B82F6",
    "neutral": "#94A3B8",
}

# Diverging — RdBu (cartographer-friendly)
DIVERGING_RDBU: list[str] = [
    "#b2182b", "#ef8a62", "#fddbc7", "#f7f7f7",
    "#d1e5f0", "#67a9cf", "#2166ac",
]


def severity_color(level: str) -> str:
    """Return a hex color for a severity/status keyword."""
    return SEMANTIC.get(level.lower().strip(), SEMANTIC["neutral"])


def categorical(n: int, *, palette: list[str] | None = None) -> list[str]:
    """Return `n` colors, cycling the chosen categorical palette."""
    base = palette or AGENCY_CATEGORICAL
    if n <= len(base):
        return base[:n]
    # cycle if more series than palette length
    return [base[i % len(base)] for i in range(n)]
