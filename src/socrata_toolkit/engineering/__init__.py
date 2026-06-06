"""Engineering pillar: construction, contracts, costs, borough analytics, materials, and infrastructure management."""

from __future__ import annotations

# NYC Street Design Manual material specs (tests import via engineering)
from ..material.compliance import (
    ADAComplianceCheckResult,
    ADAFailureSeverity,
    ComplianceStatus,
    MaintenanceScheduleCheckResult,
    MaterialCompliance,
)
from ..material.definitions import (
    ASPH_STANDARD,
    CONC_STANDARD,
    MATERIAL_DEFINITIONS,
    get_material_by_category,
    get_material_by_id,
    get_materials_by_lifecycle_cost_range,
)
from ..material.standards import (
    DefectSeverityAssessment,
    DefectType,
    MaterialCategory,
    SurfaceAssessment,
    SurfaceCondition,
)
from .borough_analysis import *
from .budget_forecast import *
from .construction_list import *
from .contract_analytics import *
from .contractor_scorecards import *
from .cost_estimator import *
from .dot_sidewalk import (
    MaterialAwareSidewalkKPI,
    SidewalkKPI,
    compute_material_aware_kpis,
    compute_sidewalk_kpis,
)
from .infrastructure import (
    AssetCondition,
    LifeCycleCostAnalysis,
    MROptimization,
    MarkovDeteriorationModel,
    evaluate_system_resiliency,
)
from .pavement import (
    NYSDOTPavementEngine,
    PavementDesignParameters,
    PavementType,
    SurfaceRating,
    evaluate_pavement_safety_risk,
)
from .ramp_analysis import (
    BoroughRampStats,
    RampCompletionReport,
    RampCompletionReportGenerator,
)

