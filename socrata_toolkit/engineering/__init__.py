"""Engineering pillar: construction, contracts, costs, borough analytics, materials."""

from __future__ import annotations

from .borough_analysis import *
from .budget_forecast import *
from .construction_list import *
from .contract_analytics import *
from .contractor_scorecards import *
from .cost_estimator import *
from .dot_sidewalk import (
    MaterialAwareSidewalkKPI,
    compute_material_aware_kpis,
    compute_sidewalk_kpis,
)

# NYC Street Design Manual material specs (tests import via engineering)
from ..material.compliance import (
    ADAComplianceCheckResult,
    ADAFailureSeverity,
    ComplianceStatus,
    MaintenanceScheduleCheckResult,
    MaterialCompliance,
)
from ..material.standards import (
    DefectSeverityAssessment,
    DefectType,
    SurfaceAssessment,
    SurfaceCondition,
)
from ..material.definitions import (
    ASPH_STANDARD,
    CONC_STANDARD,
    MATERIAL_DEFINITIONS,
    get_material_by_category,
    get_material_by_id,
    get_materials_by_lifecycle_cost_range,
)
from ..material.standards import MaterialCategory

# Alias for tests expecting SidewalkKPI (legacy name)
SidewalkKPI = MaterialAwareSidewalkKPI
