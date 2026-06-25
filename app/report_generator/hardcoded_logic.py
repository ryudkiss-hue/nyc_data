"""
Hardcoded Business Logic for NYC DOT Reporting Framework

All narrative templates, classifications, thresholds, and business rules are defined here.
This module contains ZERO dynamic logic - purely rule definitions and lookup tables.
"""

from dataclasses import dataclass


@dataclass
class MoransIClassification:
    """Moran's I spatial autocorrelation classification."""
    range_min: float
    range_max: float
    classification: str
    meaning: str
    implication: str
    recommendation: str

# PHASE B: SPATIAL CLUSTERING (Moran's I) HARDCODED RULES
MORANS_I_CLASSIFICATIONS: dict[str, dict] = {
    'STRONG_CLUSTERING': {
        'range': (0.5, 1.0),
        'meaning': 'Violations form tight geographic clusters',
        'implication': 'Common infrastructure or operational problems in specific areas',
        'recommendation': 'Deploy resources to identified cluster centers for efficiency',
        'action_steps': [
            '1. Identify geographic cluster centers using spatial kernel density',
            '2. Assign specialized crews to high-violation neighborhoods',
            '3. Investigate common infrastructure problems (drainage, materials, age)',
            '4. Coordinate with other NYC agencies (DOE, HPD) for integrated fixes',
            '5. Track cluster emergence/dissolution over time for effectiveness'
        ]
    },
    'MODERATE_CLUSTERING': {
        'range': (0.2, 0.5),
        'meaning': 'Some clustering evident, but not pronounced',
        'implication': 'Mix of area-wide and location-specific issues',
        'recommendation': 'Balance citywide initiatives with targeted neighborhood focus',
        'action_steps': [
            '1. Map cluster boundaries precisely for resource allocation',
            '2. Implement both citywide improvements AND neighborhood initiatives',
            '3. Investigate why some neighborhoods cluster while others don\'t',
            '4. Allocate resources proportionally by cluster intensity'
        ]
    },
    'RANDOM_DISTRIBUTION': {
        'range': (-0.2, 0.2),
        'meaning': 'No meaningful geographic clustering',
        'implication': 'Violations independent of location',
        'recommendation': 'Focus on violation-type solutions rather than geographic targeting',
        'action_steps': [
            '1. Analyze by violation TYPE rather than LOCATION',
            '2. Implement uniform inspection and repair protocols across all boroughs',
            '3. Focus on material durability, inspection frequency, and compliance standards',
            '4. Expect similar violation rates in all neighborhoods'
        ]
    },
    'SPATIAL_DISPERSION': {
        'range': (-1.0, -0.2),
        'meaning': 'Violations actively spread apart geographically',
        'implication': 'Possible over-correction or systematic geographic fairness',
        'recommendation': 'Investigate for geographic disparity in inspection enforcement',
        'action_steps': [
            '1. ALERT: Investigate for geographic fairness in enforcement',
            '2. Review inspector assignment patterns for bias',
            '3. Verify that inspection frequency is truly uniform across areas',
            '4. Adjust protocols if data shows systematic geographic disparity'
        ]
    }
}

# PHASE C: DISTRIBUTION CLASSIFICATION HARDCODED RULES
DISTRIBUTION_TYPES: dict[str, dict] = {
    'NORMAL': {
        'characteristics': 'Bell curve, symmetric around mean',
        'meaning': 'Violations follow predictable, natural variation',
        'action': 'Use standard resource allocation; violations are expected and managed',
        'test_recommendation': 'Use parametric tests (t-test, ANOVA)',
        'concentration': 'Moderate - evenly distributed around mean'
    },
    'RIGHT_SKEWED': {
        'characteristics': 'Tail extends right toward high values',
        'meaning': 'Most areas comply well; problem concentrated in few high-violation areas',
        'action': 'Focus resources on high-violation areas; most areas need minimal attention',
        'test_recommendation': 'Use non-parametric tests (Mann-Whitney U, Kruskal-Wallis)',
        'concentration': 'High - concentrated in upper tail'
    },
    'LEFT_SKEWED': {
        'characteristics': 'Tail extends left toward low values',
        'meaning': 'Most areas have violations; only few areas are compliant',
        'action': 'Implement citywide improvements; localized fixes insufficient',
        'test_recommendation': 'Use non-parametric tests (Mann-Whitney U, Kruskal-Wallis)',
        'concentration': 'High - concentrated in lower tail'
    },
    'BIMODAL': {
        'characteristics': 'Two distinct peaks; two populations',
        'meaning': 'Neighborhoods fall into two categories: compliant vs. non-compliant',
        'action': 'Segment by type; develop different strategies for each group',
        'test_recommendation': 'Use cluster analysis and stratified sampling',
        'concentration': 'Very high - bimodal distribution'
    }
}

# PHASE D: OUTLIER INVESTIGATION HARDCODED RULES
OUTLIER_INVESTIGATION_RECOMMENDATIONS: dict[str, dict] = {
    'HIGH_OUTLIER': {
        'meaning': 'Anomalously high violation rates',
        'root_causes': [
            'Aging infrastructure (oldest sidewalks)',
            'High pedestrian traffic (commercial corridors)',
            'Environmental factors (drainage issues, freeze-thaw cycles)',
            'Deferred maintenance cycles',
            'Proximity to construction zones',
            'Material degradation (exposure, age)'
        ],
        'investigation_steps': [
            '1. Extract historical violation timeline for location',
            '2. Compare to neighborhood average and city average',
            '3. Investigate material age, installation date, maintenance history',
            '4. Interview field staff about unique location challenges',
            '5. Review adjacent locations for systemic patterns',
            '6. Determine if outlier is persistent or transient'
        ],
        'remediation_priority': 'HIGH'
    },
    'LOW_OUTLIER': {
        'meaning': 'Anomalously low violation rates (best practices)',
        'root_causes': [
            'Newer infrastructure (recent installation/rehabilitation)',
            'Effective maintenance protocols in place',
            'Lower pedestrian traffic or more resilient area',
            'Higher quality materials used historically',
            'Regular preventive maintenance schedule',
            'Favorable environmental conditions'
        ],
        'investigation_steps': [
            '1. Extract maintenance history for location',
            '2. Interview field staff about best practices at location',
            '3. Identify material types, age, and installation methods',
            '4. Document maintenance schedule and frequency',
            '5. Compare to similar areas with higher violation rates',
            '6. Assess replicability to other locations'
        ],
        'remediation_priority': 'REPLICATE'
    }
}

# PHASE E: SEASONAL DECOMPOSITION HARDCODED RULES
SEASONAL_RESOURCE_ALLOCATION: dict[str, dict] = {
    'WINTER_PEAK': {
        'months': ['December', 'January', 'February', 'March'],
        'typical_amplitude': 0.40,  # 40% increase typical
        'resource_increase_formula': 'baseline * (1 + amplitude)',
        'recommended_staffing': 'Increase crew hours by {increase_pct:.0f}% during winter',
        'material_stocmetricle': 'Pre-position salt, sand, patching materials 30 days before peak',
        'equipment_prep': 'Service snow removal equipment, ensure adequate tire treads',
        'forecast_model': 'Bayesian seasonal autoregressive with weather integration'
    },
    'SPRING_DECLINE': {
        'months': ['April', 'May'],
        'typical_amplitude': -0.25,  # 25% decline typical
        'resource_increase_formula': 'baseline * (1 + amplitude)',
        'recommended_staffing': 'Reduce crew hours by {increase_pct:.0f}% as weather improves',
        'material_stocmetricle': 'Deplete winter stocmetricles, prepare for spring cleaning',
        'equipment_prep': 'Clean and maintain equipment, prepare for summer use',
        'forecast_model': 'Account for delayed damage from winter conditions'
    },
    'SUMMER_STABLE': {
        'months': ['June', 'July', 'August'],
        'typical_amplitude': -0.05,  # Slight decline or stable
        'resource_increase_formula': 'baseline * (1 + amplitude)',
        'recommended_staffing': 'Maintain baseline staffing',
        'material_stocmetricle': 'Minimal stocmetricle needed',
        'equipment_prep': 'Routine preventive maintenance',
        'forecast_model': 'Expect low seasonality; focus on trend'
    },
    'FALL_INCREASE': {
        'months': ['September', 'October', 'November'],
        'typical_amplitude': 0.15,  # 15% increase typical
        'resource_increase_formula': 'baseline * (1 + amplitude)',
        'recommended_staffing': 'Increase crew hours by {increase_pct:.0f}% as fall weather arrives',
        'material_stocmetricle': 'Begin stocmetricling winter materials',
        'equipment_prep': 'Service equipment for winter season',
        'forecast_model': 'Prepare for winter peak'
    }
}

# PHASE F: SLA & BAYESIAN FORECASTING HARDCODED RULES
SLA_THRESHOLDS: dict[str, dict] = {
    'HIGH': {
        'days': 14,
        'meaning': 'Data must be refreshed within 2 weeks',
        'criticality': 'CRITICAL',
        'breach_action': 'Escalate immediately to director',
        'recovery_action': 'Allocate additional resources to refresh data within 48 hours'
    },
    'MEDIUM': {
        'days': 30,
        'meaning': 'Data must be refreshed within 1 month',
        'criticality': 'HIGH',
        'breach_action': 'Flag for leadership review',
        'recovery_action': 'Schedule emergency refresh within 72 hours'
    },
    'LOW': {
        'days': 60,
        'meaning': 'Data must be refreshed within 2 months',
        'criticality': 'MEDIUM',
        'breach_action': 'Document and plan refresh',
        'recovery_action': 'Include in next scheduled refresh cycle'
    }
}

# PHASE F: RISK ASSESSMENT HARDCODED RULES
RISK_ASSESSMENT_MATRIX: dict[str, dict] = {
    'CRITICAL': {
        'probability_range': (0.75, 1.0),
        'meaning': 'Very likely to miss SLA target',
        'decision': 'MUST INVEST - Risk unacceptable if unaddressed',
        'investment_justification': 'Prevention cost << breach cost',
        'approval_threshold': 'Chief Operations Officer sign-off required'
    },
    'HIGH': {
        'probability_range': (0.50, 0.75),
        'meaning': 'Likely to miss SLA target',
        'decision': 'STRONGLY RECOMMENDED - Invest to reduce risk',
        'investment_justification': 'Expected cost savings exceed investment',
        'approval_threshold': 'Director-level sign-off required'
    },
    'MEDIUM': {
        'probability_range': (0.25, 0.50),
        'meaning': 'Moderate risk of SLA breach',
        'decision': 'OPTIONAL - Weigh against other priorities',
        'investment_justification': 'Marginal ROI; other initiatives may be higher priority',
        'approval_threshold': 'Department head approval'
    },
    'LOW': {
        'probability_range': (0.0, 0.25),
        'meaning': 'Low probability of SLA breach',
        'decision': 'OPTIONAL - Monitor situation',
        'investment_justification': 'ROI minimal; reassess if conditions change',
        'approval_threshold': 'No special approval needed'
    }
}

def classify_morans_i(morans_i_value: float) -> str:
    """
    Classify Moran's I value into hardcoded category.

    Args:
        morans_i_value: Moran's I statistic value

    Returns:
        Classification key (STRONG_CLUSTERING, MODERATE_CLUSTERING, etc.)
    """
    for classification_key, config in MORANS_I_CLASSIFICATIONS.items():
        range_min, range_max = config['range']
        if range_min <= morans_i_value <= range_max:
            return classification_key

    # Fallback
    if morans_i_value > 0.5:
        return 'STRONG_CLUSTERING'
    elif morans_i_value < -0.2:
        return 'SPATIAL_DISPERSION'
    else:
        return 'RANDOM_DISTRIBUTION'

def classify_distribution(skewness: float, kurtosis: float, bimodality_index: float = None) -> str:
    """
    Classify distribution shape using hardcoded rules.

    Args:
        skewness: Skewness coefficient
        kurtosis: Kurtosis coefficient
        bimodality_index: Optional bimodality statistic

    Returns:
        Distribution type (NORMAL, RIGHT_SKEWED, LEFT_SKEWED, BIMODAL)
    """
    # Check for bimodality first (hardcoded threshold)
    if bimodality_index is not None and bimodality_index > 0.555:
        return 'BIMODAL'

    # Skewness-based classification (hardcoded thresholds)
    if abs(skewness) < 0.5:
        return 'NORMAL'
    elif skewness > 0.5:
        return 'RIGHT_SKEWED'
    else:
        return 'LEFT_SKEWED'

def get_risk_level(prob_meets_sla: float) -> str:
    """
    Classify risk level based on probability of meeting SLA.

    Args:
        prob_meets_sla: Probability (0-1) of meeting SLA target

    Returns:
        Risk level (CRITICAL, HIGH, MEDIUM, LOW)
    """
    prob_breach = 1.0 - prob_meets_sla

    for risk_level, config in RISK_ASSESSMENT_MATRIX.items():
        range_min, range_max = config['probability_range']
        if range_min <= prob_breach <= range_max:
            return risk_level

    # Fallback
    if prob_breach > 0.75:
        return 'CRITICAL'
    elif prob_breach > 0.50:
        return 'HIGH'
    elif prob_breach > 0.25:
        return 'MEDIUM'
    else:
        return 'LOW'

def get_morans_i_config(classification: str) -> dict:
    """Get hardcoded config for Moran's I classification."""
    return MORANS_I_CLASSIFICATIONS.get(classification, MORANS_I_CLASSIFICATIONS['RANDOM_DISTRIBUTION'])

def get_distribution_config(distribution_type: str) -> dict:
    """Get hardcoded config for distribution type."""
    return DISTRIBUTION_TYPES.get(distribution_type, DISTRIBUTION_TYPES['NORMAL'])

def get_outlier_config(outlier_type: str) -> dict:
    """Get hardcoded config for outlier type."""
    return OUTLIER_INVESTIGATION_RECOMMENDATIONS.get(outlier_type, OUTLIER_INVESTIGATION_RECOMMENDATIONS['HIGH_OUTLIER'])

def get_seasonal_config(season: str) -> dict:
    """Get hardcoded config for seasonal period."""
    return SEASONAL_RESOURCE_ALLOCATION.get(season, {})

def get_risk_config(risk_level: str) -> dict:
    """Get hardcoded config for risk level."""
    return RISK_ASSESSMENT_MATRIX.get(risk_level, RISK_ASSESSMENT_MATRIX['LOW'])

def get_sla_config(sla_level: str) -> dict:
    """Get hardcoded config for SLA level."""
    return SLA_THRESHOLDS.get(sla_level, SLA_THRESHOLDS['MEDIUM'])
