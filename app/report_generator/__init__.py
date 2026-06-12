"""
NYC DOT Report Generator - Phase 3 Implementation

Generates 5 hardcoded narrative reports with dynamic value injection:
- Phase B: Spatial Clustering (SCR framework)
- Phase C: Distribution Analysis (BAB framework)
- Phase D: Outlier Investigation (Hero's Journey)
- Phase E: Seasonal Decomposition (Problem-Solution-Proof)
- Phase F: SLA Forecasting (Decision-Consequence-Action)

All narrative structures are hardcoded; only values are injected from MotherDuck.
"""

from .hardcoded_logic import (
    DISTRIBUTION_TYPES,
    MORANS_I_CLASSIFICATIONS,
    RISK_ASSESSMENT_MATRIX,
    classify_distribution,
    classify_morans_i,
    get_risk_level,
)
from .phase_b_reporter import PhaseBReporter, generate_phase_b_report
from .phase_c_reporter import PhaseCReporter, generate_phase_c_report
from .phase_d_reporter import PhaseDReporter, generate_phase_d_report
from .phase_e_reporter import PhaseEReporter, generate_phase_e_report
from .phase_f_reporter import PhaseFReporter, generate_phase_f_report
from .value_injector import ValueInjector, create_injector, inject_into_template

__all__ = [
    # Hardcoded logic
    'classify_morans_i',
    'classify_distribution',
    'get_risk_level',
    'MORANS_I_CLASSIFICATIONS',
    'DISTRIBUTION_TYPES',
    'RISK_ASSESSMENT_MATRIX',
    # Value injection
    'ValueInjector',
    'create_injector',
    'inject_into_template',
    # Reporters
    'PhaseBReporter',
    'PhaseCReporter',
    'PhaseDReporter',
    'PhaseEReporter',
    'PhaseFReporter',
    # Factory functions
    'generate_phase_b_report',
    'generate_phase_c_report',
    'generate_phase_d_report',
    'generate_phase_e_report',
    'generate_phase_f_report',
]

__version__ = '1.0.0'
