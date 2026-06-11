"""
Dashboards Module: Unified Dash Application for NYC DOT SIM Workflows.

Production dashboard with 30+ visualizations across 6 analytical areas:
- Home: Key metrics and status
- Violations: Violation analysis by borough, material, time
- Ramps: Ramp accessibility and completion tracking
- Permits: Permit coordination and conflict detection
- Geographic: GIS mapping with hotspot analysis
- Analytics: Advanced analytics (CUSUM, Bayesian, clustering)

All visualizations use standardized units system from Phase 1.
"""

from .unified_dashboard import app

__all__ = ["app"]
