"""
NYC Street Design Manual Material Taxonomy - Standard Definitions

Pre-loaded material specifications for all standard NYC sidewalk materials.
Includes complete design standards, maintenance schedules, lifecycle costs,
and environmental factors based on NYC Street Design Manual and industry standards.

All material definitions reference:
- NYC Street Design Manual (https://www.nycstreetdesign.info/)
- NYC Administrative Code Title 34
- ASCE, ACI, NAPA industry standards
- Real NYC street maintenance data and costs

Standards: Python 3.9+, type hints, comprehensive docstrings
"""

from __future__ import annotations

import logging

from socrata_toolkit.material.standards import (
    MaintenanceSchedule,
    MaterialCategory,
    MaterialSpecification,
)

logger = logging.getLogger(__name__)


# ============================================================================
# MAINTENANCE SCHEDULES - Material-specific maintenance cycles
# ============================================================================

ASPHALT_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=3,
    preventive_overlay_years=7,
    lifecycle_years=20,
    climate_adjustment={
        "freeze_thaw_zone": -2,
        "high_salt_exposure": -2,
        "high_traffic": -1,
    },
    activities={
        "seal_coat": "Hot asphalt emulsion seal coat every 3 years",
        "crack_seal": "Crack sealing and filling every 2 years or as needed",
        "pothole_repair": "Pothole repair as needed (emergency))",
        "overlay": "Preventive overlay at year 7",
        "full_reconstruction": "Full reconstruction at year 20 or earlier if PCI < 25",
    }
)

CONCRETE_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=5,
    preventive_overlay_years=15,
    lifecycle_years=30,
    climate_adjustment={
        "freeze_thaw_zone": -5,
        "high_salt_exposure": -5,
        "high_traffic": -2,
    },
    activities={
        "joint_sealing": "Joint sealing and cleaning every 5 years",
        "crack_repair": "Crack routing and sealing every 3 years or as needed",
        "spall_repair": "Spall repair as needed (safety critical)",
        "overlay": "Overlay or resurfacing at year 15",
        "full_reconstruction": "Full reconstruction at year 30 or earlier if PCI < 20",
    }
)

PERMEABLE_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=2,
    preventive_overlay_years=10,
    lifecycle_years=20,
    climate_adjustment={
        "freeze_thaw_zone": -3,
        "high_salt_exposure": -2,
        "clogging_risk": -2,
    },
    activities={
        "vacuum_sweeping": "Vacuum sweeping every 6 months to maintain infiltration",
        "pressure_washing": "Pressure washing every 2 years",
        "clogging_remediation": "Clogging removal as needed (critical for function)",
        "overlay": "Overlay at year 10 if infiltration rate falls below 85%",
        "full_reconstruction": "Full reconstruction at year 20",
    }
)

SPECIALTY_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=3,
    preventive_overlay_years=12,
    lifecycle_years=25,
    climate_adjustment={
        "freeze_thaw_zone": -3,
        "high_salt_exposure": -2,
    },
    activities={
        "mortar_joint_repair": "Mortar joint repair and repointing every 3 years",
        "unit_replacement": "Individual unit/paver replacement as needed",
        "cleaning": "Pressure washing and cleaning every 2 years",
        "overlay": "Overlay or relay at year 12",
        "full_reconstruction": "Full reconstruction at year 25",
    }
)

METAL_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=1,
    preventive_overlay_years=8,
    lifecycle_years=15,
    climate_adjustment={
        "high_salt_exposure": -3,
        "high_traffic": -1,
    },
    activities={
        "cleaning": "Weekly cleaning and debris removal",
        "rust_treatment": "Rust treatment and coating annually",
        "replacement": "Component replacement as needed",
        "full_replacement": "Full replacement at year 15 or if structural integrity compromised",
    }
)


# ============================================================================
# MATERIAL SPECIFICATIONS - All standard NYC sidewalk materials
# ============================================================================

# HOT MIX ASPHALT (ASPHALT_STANDARD)
ASPH_STANDARD = MaterialSpecification(
    material_id="ASPH-NYC-001",
    category=MaterialCategory.ASPHALT,
    name="Hot Mix Asphalt (HMA), 12.5mm SuperPave",
    description=(
        "Standard hot mix asphalt with 12.5mm nominal maximum aggregate size, "
        "SuperPave design, widely used for NYC sidewalks. Most common sidewalk surface. "
        "Good value, proven performance in NYC climate."
    ),
    design_standards={
        "thickness_inches": 2.0,
        "compaction_percent": 96,
        "binder_grade": "PG58-28",
        "air_voids_percent": 4.0,
        "vma_percent": 14.0,
        "aggregate_size_mm": 12.5,
        "slip_resistance_bpn": 65,  # British Pendulum Number
    },
    maintenance_schedule=ASPHALT_MAINTENANCE,
    lifecycle_years=20,
    environmental_factors={
        "freeze_thaw": "Critical in NYC climate",
        "salt_exposure": "High - requires seal coating",
        "uv_degradation": "Moderate - seal coat slows oxidation",
        "stormwater_infiltration": "None - requires drainage",
    },
    cost_per_sqft=2.50,
    lifecycle_cost_per_sqft=12.00,
    sustainability_score=45,  # Lower due to petroleum-based
    carbon_footprint_kg_per_sqft=0.85,
    applicable_ada_rules=[
        "ADA-1.2.1",  # Accessible routes width
        "ADA-1.3.1",  # Walking surface slip resistance
        "ADA-1.5.1",  # Ground surfaces firmness
        "ADA-1.6.1",  # Changes in level
    ],
    maintenance_procedures={
        "seal_coat": (
            "Apply hot asphalt emulsion seal coat (RS-2) at 0.25-0.35 gal/sy. "
            "Add 100-200 lbs/sy of cover aggregate. Cure 24-48 hours. "
            "Reduces oxidation, extends life by 5-7 years."
        ),
        "crack_sealing": (
            "Route cracks to 0.5\" wide, 0.75\" deep. Clean with compressed air. "
            "Fill with hot-applied rubber crack sealant. Seal prevents water infiltration."
        ),
        "pothole_repair": (
            "Remove failed material to solid edges. Clean and tack coat. "
            "Fill with HMA, compact to 96%. Temporary patch: cold patch HMA. "
            "Permanent: saw-cut, full-depth repair."
        ),
        "full_overlay": (
            "Remove surface irregularities. Mill if needed. Tack coat entire area. "
            "Lay 1.5-2\" HMA overlay, compact to 96%. Profile control essential."
        ),
    },
    nyc_code_references=[
        "NYC Administrative Code Title 34",
        "DOT Sidewalk Inspection Manual",
        "Local Law 60 - Sidewalk Maintenance",
    ],
    industry_standards=[
        "ASCE MOP 22 - Design of Urban Asphalt Pavements",
        "NAPA QIP - Quality Improvement Program",
        "ASTM D3665 - Application of Hot-Mix Asphalt",
    ],
    notes="Most common material on NYC sidewalks. Local cost data from DOT 2024."
)

# POROUS/PERMEABLE ASPHALT
ASPH_POROUS = MaterialSpecification(
    material_id="ASPH-NYC-002",
    category=MaterialCategory.ASPHALT,
    name="Porous Asphalt (Open-Graded Friction Course)",
    description=(
        "Open-graded asphalt mix with high permeability (15-20% infiltration). "
        "Reduces stormwater runoff, improves drainage, supports environmental goals. "
        "Higher maintenance due to clogging risk."
    ),
    design_standards={
        "thickness_inches": 2.5,
        "compaction_percent": 94,
        "binder_grade": "PG64-28",
        "air_voids_percent": 18.0,
        "infiltration_rate_in_per_hour": 360,  # Very high
        "stone_on_stone_contact": True,
        "aggregate_size_mm": 19.0,
    },
    maintenance_schedule=PERMEABLE_MAINTENANCE,
    lifecycle_years=20,
    environmental_factors={
        "stormwater_infiltration": "Excellent - major benefit",
        "clogging_risk": "High - requires regular maintenance",
        "freeze_thaw": "Higher stress due to water retention",
        "pollutant_filtration": "Good - filters particles and pollutants",
    },
    cost_per_sqft=3.25,
    lifecycle_cost_per_sqft=18.50,  # Higher due to frequent maintenance
    sustainability_score=78,  # High due to stormwater benefits
    carbon_footprint_kg_per_sqft=0.90,
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
    ],
    maintenance_procedures={
        "vacuum_sweeping": (
            "Vacuum sweep entire surface every 6 months to prevent clogging. "
            "Use regenerative air sweeper (preferred) or vacuum trucks. "
            "Critical for maintaining infiltration function."
        ),
        "pressure_washing": (
            "Pressure wash every 2 years (1000-1500 PSI, 3-4 GPM). "
            "Remove accumulated sediment and pollutants. "
            "Do not exceed 1500 PSI to avoid aggregate dislodging."
        ),
        "full_replacement": (
            "Replace when infiltration rate falls below 180 in/hr (50% of design). "
            "Remove to subgrade, replace full thickness with new material."
        ),
    },
    nyc_code_references=[
        "NYC Environmental Quality Review (CEQR) Guidelines",
        "DEP Stormwater Pollution Prevention Plan (SWPPP)",
    ],
    industry_standards=[
        "NAPA IS 132 - Porous Asphalt Pavements",
        "ASCE/EWRI Permeable Pavement Guidelines",
    ],
    notes="High maintenance cost justified by stormwater benefit. Growing use in NYC."
)

# PORTLAND CEMENT CONCRETE
CONC_STANDARD = MaterialSpecification(
    material_id="CONC-NYC-001",
    category=MaterialCategory.CONCRETE,
    name="Portland Cement Concrete (PCC), Air-Entrained, 4\" Jointed",
    description=(
        "Standard Portland cement concrete sidewalk with 4\" jointed construction. "
        "Excellent durability, very long service life (25-30 years). "
        "Higher initial cost but lower maintenance. Common in commercial areas."
    ),
    design_standards={
        "thickness_inches": 4.0,
        "compressive_strength_psi": 3500,
        "air_content_percent": 6,
        "water_cement_ratio": 0.45,
        "joint_spacing_feet": 4,
        "joint_type": "doweled butt joints",
        "finish": "broom finish for slip resistance",
        "slip_resistance_bpn": 70,
    },
    maintenance_schedule=CONCRETE_MAINTENANCE,
    lifecycle_years=30,
    environmental_factors={
        "freeze_thaw": "Excellent with air entrainment",
        "salt_exposure": "Good - avoid deicing salt damage",
        "uv_degradation": "None",
        "alkali_aggregate_reaction": "Low with quality materials",
    },
    cost_per_sqft=4.50,
    lifecycle_cost_per_sqft=14.00,  # Lower maintenance = lower total cost
    sustainability_score=50,  # Moderate - cement is energy-intensive
    carbon_footprint_kg_per_sqft=0.95,  # Cement production is carbon-intensive
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-1.7.1",  # Protruding objects
    ],
    maintenance_procedures={
        "joint_sealing": (
            "Clean joints to 1.5x joint width, 1\" deep. Dry completely. "
            "Apply joint sealant (polyurethane or silicone). "
            "Maintain seal every 5-7 years. Prevents water infiltration."
        ),
        "crack_repair": (
            "Small cracks (<0.1\"): seal with low-viscosity polyurethane. "
            "Medium cracks: route and seal with elastomeric sealant. "
            "Prevents spalling and extends life."
        ),
        "spall_repair": (
            "Small spalls: patch with self-consolidating concrete. "
            "Large spalls: remove affected area, prepare subgrade, place new concrete. "
            "Safety critical - address promptly."
        ),
    },
    nyc_code_references=[
        "NYC Administrative Code Title 34",
        "DOT Sidewalk Design Standards",
    ],
    industry_standards=[
        "ACI 302 - Concrete Floor Finishes",
        "ASTM C94 - Ready-Mix Concrete",
        "PCA Design of Concrete Pavements",
    ],
    notes="Premium material for high-value districts. NYC has extensive concrete sidewalks."
)

# PERVIOUS CONCRETE
CONC_POROUS = MaterialSpecification(
    material_id="CONC-NYC-002",
    category=MaterialCategory.CONCRETE,
    name="Pervious Concrete, High-Permeability Mix",
    description=(
        "Concrete mix with high water permeability (10-50 gal/min/sf). "
        "Supports stormwater infiltration and groundwater recharge. "
        "Emerging sustainable material gaining traction in NYC."
    ),
    design_standards={
        "thickness_inches": 4.0,
        "compressive_strength_psi": 2500,  # Lower than standard PCC
        "porosity_percent": 15,
        "infiltration_rate_in_per_hour": 480,
        "air_void_ratio": 0.30,
        "aggregate_gradation": "gap-graded",
        "binder_paste_volume_percent": 10,
    },
    maintenance_schedule=PERMEABLE_MAINTENANCE,
    lifecycle_years=25,
    environmental_factors={
        "stormwater_infiltration": "Excellent - primary benefit",
        "clogging_risk": "Moderate - requires more maintenance than asphalt",
        "freeze_thaw": "Good with air entrainment",
        "pollutant_filtration": "Good - natural filtration",
    },
    cost_per_sqft=5.50,
    lifecycle_cost_per_sqft=20.00,
    sustainability_score=82,  # High due to stormwater and infiltration
    carbon_footprint_kg_per_sqft=0.98,
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
    ],
    maintenance_procedures={
        "vacuum_sweeping": (
            "Vacuum sweep every 6-12 months to prevent clogging. "
            "More aggressive clogging than porous asphalt."
        ),
        "pressure_washing": (
            "Pressure wash every 2-3 years (500-1000 PSI, gentle). "
            "Use low pressure to avoid damage."
        ),
    },
    nyc_code_references=[
        "NYC DEP Stormwater Regulations",
        "CEQR Guidelines - Permeable Pavements",
    ],
    industry_standards=[
        "NAPA/APA Pervious Concrete Pavements Guidelines",
        "ACI 522 - Pervious Concrete",
    ],
    notes="Emerging market in NYC for sustainability goals. Higher initial cost."
)

# NATURAL STONE / BLUESTONE
STONE_NATURAL = MaterialSpecification(
    material_id="STONE-NYC-001",
    category=MaterialCategory.BRICK_STONE,
    name="Natural Stone (Bluestone), 1.5\" Thickness",
    description=(
        "Premium natural bluestone (slate) paving. Historic and elegant. "
        "Very durable and beautiful, widely used in high-value Manhattan neighborhoods. "
        "High initial and maintenance cost due to specialty materials."
    ),
    design_standards={
        "thickness_inches": 1.5,
        "stone_type": "bluestone (slate)",
        "surface_finish": "split face or honed",
        "mortar_type": "Portland cement, low alkali",
        "joint_width_inches": 0.25,
        "bed_depth_inches": 1.0,
        "slip_resistance_bpn": 75,  # Excellent
    },
    maintenance_schedule=SPECIALTY_MAINTENANCE,
    lifecycle_years=50,  # Very long lifespan
    environmental_factors={
        "freeze_thaw": "Excellent - natural stone resistant",
        "salt_exposure": "Good - resistant to salt",
        "staining": "Moderate - can stain, may need periodic cleaning",
        "durability": "Excellent - 50+ year lifespan typical",
    },
    cost_per_sqft=15.00,  # Premium material
    lifecycle_cost_per_sqft=28.00,
    sustainability_score=70,  # Quarrying impact but very long-lived
    carbon_footprint_kg_per_sqft=1.20,
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-1.8.1",  # Gratings and openings
    ],
    maintenance_procedures={
        "cleaning": (
            "Pressure wash as needed (use 500-800 PSI maximum to avoid damage). "
            "Use biodegradable detergent for stain removal. "
            "Polish with natural stone cleaner periodically."
        ),
        "joint_repair": (
            "Repoint mortar joints every 10-15 years as needed. "
            "Use low-alkali Portland cement to match original. "
            "Prevents water penetration and maintains appearance."
        ),
        "crack_repair": (
            "Seal existing cracks with water-based sealant. "
            "Large cracks may require stone replacement. "
            "Address promptly to prevent further damage."
        ),
        "stone_replacement": (
            "Replace individual damaged stones as needed. "
            "Cost-effective: replace only damaged units. "
            "High-value maintenance on premium installations."
        ),
    },
    nyc_code_references=[
        "NYC Historic Preservation Commission guidelines",
        "NYC Administrative Code Title 34",
    ],
    industry_standards=[
        "ANSI A300 - Stone Installation Standards",
        "Natural Stone Institute Guidelines",
    ],
    notes="Very common in historic districts and high-value areas. NYC has extensive bluestone inventory."
)

# CLAY BRICK PAVERS
BRICK_CLAY = MaterialSpecification(
    material_id="BRICK-NYC-001",
    category=MaterialCategory.BRICK_STONE,
    name="Clay Brick Pavers, Modular Pattern",
    description=(
        "Traditional clay brick pavers in modular pattern. Historic aesthetic, "
        "good durability, moderate maintenance. Common in historic districts "
        "and specialized pedestrian areas."
    ),
    design_standards={
        "brick_size_inches": "3.625 x 7.625",
        "thickness_inches": 2.25,
        "pattern": "running bond or herringbone",
        "compressive_strength_psi": 3000,
        "mortar_type": "Type S mortar",
        "joint_width_inches": 0.375,
        "bed_type": "sand or mortar",
        "slip_resistance_bpn": 68,
    },
    maintenance_schedule=SPECIALTY_MAINTENANCE,
    lifecycle_years=25,
    environmental_factors={
        "freeze_thaw": "Good - durable clay",
        "salt_exposure": "Moderate - some salt damage possible",
        "moisture": "Can be damaged by excessive moisture",
        "color_retention": "Fades slightly over time",
    },
    cost_per_sqft=8.50,
    lifecycle_cost_per_sqft=20.00,
    sustainability_score=65,  # Natural material, kiln-fired
    carbon_footprint_kg_per_sqft=1.10,
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
    ],
    maintenance_procedures={
        "mortar_repointing": (
            "Repoint mortar joints every 5-7 years. Use Type S mortar. "
            "Clean joints, tuck-point with matching mortar. "
            "Prevents water infiltration and maintains structural integrity."
        ),
        "cleaning": (
            "Pressure wash periodically (use ≤1000 PSI). "
            "Use mild detergent and natural bristle brush. "
            "Maintain appearance and remove pollutants."
        ),
        "unit_replacement": (
            "Replace damaged bricks individually as needed. "
            "Cost-effective for isolated damage. "
            "Match color and texture to existing."
        ),
    },
    nyc_code_references=[
        "NYC Historic Preservation Commission guidelines",
        "DOT Brick Sidewalk Standards",
    ],
    industry_standards=[
        "ASTM C902 - Clay Brick Pavements",
        "Brick Industry Association Guidelines",
    ],
    notes="Historic material commonly seen in older NYC neighborhoods."
)

# ADA TRUNCATED DOMES / TACTILE WARNING SURFACES
METAL_ADA_DOMES = MaterialSpecification(
    material_id="METAL-NYC-001",
    category=MaterialCategory.METAL,
    name="ADA Truncated Dome Warning Surface, Cast Iron",
    description=(
        "Cast iron or cast-in-place concrete warning surface with truncated domes "
        "(detectable warning features per ADA). Required at curb ramps, platform edges, "
        "and transit stations. Critical ADA compliance element."
    ),
    design_standards={
        "dome_height_inches": 0.5,
        "dome_diameter_inches": 0.9,
        "base_diameter_inches": 0.5,
        "center_to_center_spacing_inches": 1.6,
        "contrasting_color": "High contrast to walking surface",
        "material": "cast iron or integral to concrete",
        "slip_resistance_bpn": 65,  # Must not be slippery
    },
    maintenance_schedule=METAL_MAINTENANCE,
    lifecycle_years=15,
    environmental_factors={
        "wear_resistance": "High - resistant to foot traffic",
        "rust_risk": "Moderate if cast iron - requires coating",
        "visibility": "Maintains visual contrast",
        "tactile_sensitivity": "Remains tactilely detectable when worn",
    },
    cost_per_sqft=45.00,  # Very expensive but critical
    lifecycle_cost_per_sqft=65.00,
    sustainability_score=40,  # Iron production and coating chemicals
    carbon_footprint_kg_per_sqft=2.50,
    applicable_ada_rules=[
        "ADA-1.6.1",  # Detectable warning (required)
        "ADA-1.7.1",  # Visual contrast required
    ],
    maintenance_procedures={
        "cleaning": (
            "Clean weekly to maintain tactile detection and visual contrast. "
            "Remove debris and buildup. Critical for ADA function."
        ),
        "rust_treatment": (
            "Treat rust spots immediately with appropriate coating. "
            "Annual rust inspection and touch-up. Maintain protective coating."
        ),
        "unit_replacement": (
            "Replace units that become undetectable (domes worn smooth). "
            "Address promptly - ADA non-compliance risk."
        ),
    },
    nyc_code_references=[
        "NYC DOT ADA Compliance Standards",
        "ADA Accessibility Guidelines 28 CFR 36",
    ],
    industry_standards=[
        "ASTM F1144 - Detectable Warning Surface Specifications",
        "ADA Standards for Accessible Design",
    ],
    notes="Critical ADA compliance element. High maintenance but mandatory for accessibility."
)

# PERMEABLE PAVERS (UNIT PAVERS)
PAVER_UNIT = MaterialSpecification(
    material_id="PAVER-NYC-001",
    category=MaterialCategory.PERMEABLE,
    name="Permeable Unit Pavers, Plastic Cellular System",
    description=(
        "Open-cellular plastic pavers filled with gravel or permeable paver units. "
        "Growing popularity for green infrastructure and stormwater management. "
        "Allows vegetation growth and infiltration. Specialized maintenance needs."
    ),
    design_standards={
        "paver_type": "open-cellular plastic grid",
        "cell_size_inches": "1-2",
        "depth_inches": 2.0,
        "fill_material": "permeable pavers or recycled plastic",
        "infiltration_rate_in_per_hour": 600,  # Very high
        "percentage_open_area": 60,
    },
    maintenance_schedule=PERMEABLE_MAINTENANCE,
    lifecycle_years=20,
    environmental_factors={
        "stormwater_infiltration": "Excellent",
        "vegetation_support": "Good - can support grasses/plants",
        "uv_degradation": "Moderate - plastic degrades with sun exposure",
        "clogging": "High risk - requires frequent maintenance",
    },
    cost_per_sqft=4.00,
    lifecycle_cost_per_sqft=16.00,
    sustainability_score=75,  # Good due to infiltration, green benefits
    carbon_footprint_kg_per_sqft=0.70,  # Lower than many alternatives
    applicable_ada_rules=[
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",  # Firmness and stability important
    ],
    maintenance_procedures={
        "vacuum_sweeping": (
            "Vacuum sweep every 3-4 months to prevent clogging. "
            "More frequent than typical due to porous nature."
        ),
        "fill_material_replacement": (
            "Replace fill material every 2-3 years or as needed. "
            "Remove clogged fill, replace with fresh material."
        ),
        "vegetation_management": (
            "Trim grass/plants quarterly if applicable. Maintain walkability. "
            "Remove debris and invasive plants."
        ),
    },
    nyc_code_references=[
        "NYC DEP Stormwater Management Guidelines",
        "CEQR Permeable Pavement Standards",
    ],
    industry_standards=[
        "ASCE/EWRI Permeable Pavement Design",
        "NAPA Permeable Pavements Guide",
    ],
    notes="Emerging green infrastructure material. Higher maintenance but sustainability benefits."
)

# RECYCLED RUBBER MATS (SPECIALTY - ADA TACTILE)
RUBBER_MATS = MaterialSpecification(
    material_id="RUBBER-NYC-001",
    category=MaterialCategory.COMPOSITE,
    name="Recycled Rubber Mats, Textured Surface",
    description=(
        "Mats made from recycled rubber with textured/tactile surface. "
        "Used in playgrounds, transit areas, and specialized accessibility zones. "
        "Provides cushioning and slip resistance. Growing market for sustainability."
    ),
    design_standards={
        "thickness_inches": 1.5,
        "density_lbs_per_cubic_foot": 110,
        "compression_resistance": "High",
        "surface_texture": "Textured or studded for grip",
        "slip_resistance_bpn": 80,  # Excellent
        "recycled_content_percent": 100,
    },
    maintenance_schedule=METAL_MAINTENANCE,  # Similar frequent maintenance
    lifecycle_years=12,
    environmental_factors={
        "uv_degradation": "Moderate - rubber degrades in sun",
        "thermal_expansion": "High - expands in heat",
        "odor": "May have slight odor in warm weather",
        "recycled_content": "100% from waste tires",
    },
    cost_per_sqft=6.00,
    lifecycle_cost_per_sqft=18.00,
    sustainability_score=88,  # High - 100% recycled content
    carbon_footprint_kg_per_sqft=0.0,  # Recycled content; net carbon benefit tracked separately
    applicable_ada_rules=[
        "ADA-1.3.1",  # Slip resistance
        "ADA-1.5.1",  # Surface properties
    ],
    maintenance_procedures={
        "cleaning": "Hose down and sweep weekly. Remove debris buildup.",
        "surface_inspection": (
            "Monthly inspection for tears, compression set, or separation. "
            "Address damage promptly to prevent further deterioration."
        ),
        "unit_replacement": (
            "Replace mats with permanent deformation or degradation. "
            "Typically 10-12 year lifespan with proper maintenance."
        ),
    },
    nyc_code_references=[
        "NYC DOT Accessible Sidewalk Standards",
    ],
    industry_standards=[
        "ASTM F1951 - Playground Surface Impact Attenuation",
        "EPA Sustainable Materials Management",
    ],
    notes="Recycled content material growing in NYC. Used in accessibility zones."
)


# ============================================================================
# MATERIAL DEFINITIONS REGISTRY - Complete dictionary for lookup
# ============================================================================

MATERIAL_DEFINITIONS: dict[str, MaterialSpecification] = {
    # Asphalt materials
    "ASPH_STANDARD": ASPH_STANDARD,
    "ASPH_POROUS": ASPH_POROUS,
    # Concrete materials
    "CONC_STANDARD": CONC_STANDARD,
    "CONC_POROUS": CONC_POROUS,
    # Natural stone
    "STONE_NATURAL": STONE_NATURAL,
    # Brick
    "BRICK_CLAY": BRICK_CLAY,
    # Metal and ADA
    "METAL_ADA_DOMES": METAL_ADA_DOMES,
    # Permeable/specialty
    "PAVER_UNIT": PAVER_UNIT,
    "RUBBER_MATS": RUBBER_MATS,
}

# Lookup by material ID (internal reference)
MATERIAL_DEFINITIONS_BY_ID: dict[str, MaterialSpecification] = {
    spec.material_id: spec for spec in MATERIAL_DEFINITIONS.values()
}


def get_material_by_id(material_id: str) -> MaterialSpecification | None:
    """Retrieve material specification by material ID.

    Args:
        material_id: Material ID (e.g., 'ASPH-NYC-001')

    Returns:
        MaterialSpecification or None if not found
    """
    return MATERIAL_DEFINITIONS_BY_ID.get(material_id)


def get_material_by_category(category: MaterialCategory) -> list[MaterialSpecification]:
    """Get all materials in a specific category.

    Args:
        category: MaterialCategory to filter

    Returns:
        List of MaterialSpecification objects
    """
    return [spec for spec in MATERIAL_DEFINITIONS.values() if spec.category == category]


def get_materials_by_lifecycle_cost_range(
    min_cost: float, max_cost: float
) -> list[MaterialSpecification]:
    """Get materials within a lifecycle cost range.

    Useful for budget-constrained material selection.

    Args:
        min_cost: Minimum lifecycle cost per sqft
        max_cost: Maximum lifecycle cost per sqft

    Returns:
        List of qualified materials
    """
    return [
        spec
        for spec in MATERIAL_DEFINITIONS.values()
        if min_cost <= spec.lifecycle_cost_per_sqft <= max_cost
    ]


logger.info(
    f"Loaded {len(MATERIAL_DEFINITIONS)} standard NYC material specifications"
)
