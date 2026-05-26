"""Engineering pillar: construction, contracts, costs, borough analytics, materials."""

from __future__ import annotations

# NYC Street Design Manual material specs (tests import via engineering)
from ..material.compliance import (  # noqa: F401
    ADAComplianceCheckResult,
    ADAFailureSeverity,
    ComplianceStatus,
    MaintenanceScheduleCheckResult,
    MaterialCompliance,
)
from ..material.definitions import (  # noqa: F401
    ASPH_STANDARD,
    CONC_STANDARD,
    MATERIAL_DEFINITIONS,
    get_material_by_category,
    get_material_by_id,
    get_materials_by_lifecycle_cost_range,
)
from ..material.standards import (  # noqa: F401
    DefectSeverityAssessment,
    DefectType,
    MaterialCategory,
    SurfaceAssessment,
    SurfaceCondition,
)
from .borough_analysis import *  # noqa: F401
from .budget_forecast import *  # noqa: F401
from .construction_list import *  # noqa: F401
from .contract_analytics import *  # noqa: F401
from .contractor_scorecards import *  # noqa: F401
from .cost_estimator import *  # noqa: F401
from .dot_sidewalk import (  # noqa: F401
    MaterialAwareSidewalkKPI,
    SidewalkKPI,
    compute_material_aware_kpis,
    compute_sidewalk_kpis,
)

