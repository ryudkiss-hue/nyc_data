-- ============================================================================
-- NYC Street Design Manual Domain Model - Reference Dimensions
-- ============================================================================
-- Purpose: Codify NYC DOT domain models as immutable reference dimensions
-- Standards: PostgreSQL, idempotent (IF NOT EXISTS), referencing SDM sections
-- Author: NYC DOT Sidewalk Toolkit
-- ============================================================================

-- =============================================================================
-- dim_materials: Material types from NYC Street Design Manual Section 4
-- =============================================================================
-- Codifies material guidance per NYC Street Design Manual Sections 4.1-4.8
-- Classification: standardized vs. distinctive vs. historic vs. pilot
CREATE TABLE IF NOT EXISTS dim_materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(128) NOT NULL UNIQUE,
    material_category VARCHAR(64) NOT NULL,
    -- Category: asphalt, concrete, permeable_surfaces, specialty, color_treatments
    sdm_section VARCHAR(16) NOT NULL,
    -- Section reference (e.g., "4.1", "4.4", "4.7", "4.9")
    classification VARCHAR(32) NOT NULL DEFAULT 'standardized',
    -- standardized | distinctive | historic | pilot
    cost_per_sqft DECIMAL(10, 4),
    -- Cost in USD per square foot from SDM guidance
    lifespan_years INT,
    -- Expected lifespan in years from SDM specifications
    maintenance_frequency VARCHAR(64),
    -- Maintenance interval (e.g., "every 5 years", "annual", "as-needed")
    description TEXT,
    -- Detailed description from SDM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert material taxonomy from NYC Street Design Manual Section 4
INSERT INTO dim_materials 
    (material_name, material_category, sdm_section, classification, cost_per_sqft, lifespan_years, maintenance_frequency, description)
VALUES
    ('Hot Mix Asphalt (HMA)', 'asphalt', '4.1', 'standardized', 2.50, 12, 'every 5 years', 
     'Standard asphalt pavement for sidewalks. SDM Section 4.1 specifies mix design and placement requirements.'),
    ('Stone Matrix Asphalt (SMA)', 'asphalt', '4.2', 'distinctive', 3.75, 15, 'every 7 years',
     'High-performance asphalt with improved durability and noise reduction. SDM Section 4.2 details specifications.'),
    ('Open-Graded Friction Course (OGFC)', 'asphalt', '4.3', 'standardized', 3.25, 10, 'every 4 years',
     'Porous asphalt for improved drainage and safety. SDM Section 4.3 covers design and maintenance.'),
    ('Portland Cement Concrete (PCC)', 'concrete', '4.4', 'standardized', 4.00, 25, 'every 10 years',
     'Standard concrete sidewalk. SDM Section 4.4 specifies reinforcement, finish, and tolerance requirements.'),
    ('Reinforced Concrete Slabs', 'concrete', '4.5', 'standardized', 4.50, 30, 'every 12 years',
     'Reinforced concrete for high-traffic areas. SDM Section 4.5 details rebar and joint design.'),
    ('Decorative Concrete', 'concrete', '4.6', 'distinctive', 6.00, 25, 'every 8 years',
     'Stamped or colored concrete for distinctive streetscapes. SDM Section 4.6 specifies durability requirements.'),
    ('Permeable Pavers', 'permeable_surfaces', '4.7', 'pilot', 8.00, 20, 'every 3 years',
     'Permeable unit pavers for stormwater management. SDM Section 4.7 covers installation and maintenance.'),
    ('Pervious Concrete', 'permeable_surfaces', '4.7', 'pilot', 5.50, 20, 'every 5 years',
     'Porous concrete allowing water infiltration. SDM Section 4.7 details mix design and durability.'),
    ('Granite Block Pavement', 'specialty', '4.8', 'historic', 12.00, 50, 'every 10 years',
     'Historic granite block pavement for preservation areas. SDM Section 4.8 specifies restoration requirements.'),
    ('Vitreous Tile', 'specialty', '4.8', 'distinctive', 9.00, 40, 'every 15 years',
     'Durable decorative tile for special districts. SDM Section 4.8 covers installation and replacement.'),
    ('Red Asphalt (Traffic Calming)', 'color_treatments', '4.9', 'distinctive', 3.50, 12, 'every 3 years',
     'Colored asphalt for traffic calming and wayfinding. SDM Section 4.9 specifies color standards and reflectivity.'),
    ('Green Asphalt (Permeable)', 'color_treatments', '4.9', 'pilot', 4.25, 10, 'every 4 years',
     'Colored permeable asphalt for stormwater management. SDM Section 4.9 covers environmental specifications.')
ON CONFLICT (material_name) DO NOTHING;

-- =============================================================================
-- dim_pavement_markings: Pavement marking standards from SDM Section 5
-- =============================================================================
-- Codifies marking standards for visibility, durability, and compliance
CREATE TABLE IF NOT EXISTS dim_pavement_markings (
    marking_id SERIAL PRIMARY KEY,
    marking_type VARCHAR(64) NOT NULL UNIQUE,
    -- Type: crosswalk, wayfinding_arrow, dashed_line, solid_line, corner_box, loading_zone
    color VARCHAR(32) NOT NULL,
    -- Color designation (white, yellow, blue, etc.)
    color_hex VARCHAR(7),
    -- Hex color code for digital rendering
    reflectivity_req VARCHAR(64) NOT NULL,
    -- Reflectivity requirement (e.g., "Type III minimum", "high visibility")
    sdm_reference VARCHAR(16),
    -- SDM Section reference
    replacement_interval_years INT DEFAULT 3,
    -- How often markings should be repainted
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert pavement marking standards from SDM Section 5
INSERT INTO dim_pavement_markings
    (marking_type, color, color_hex, reflectivity_req, sdm_reference, replacement_interval_years, description)
VALUES
    ('Crosswalk', 'white', '#FFFFFF', 'Type III minimum', '5.1', 2, 'Standard pedestrian crosswalk markings with high visibility retroreflective tape.'),
    ('Wayfinding Arrow', 'white', '#FFFFFF', 'Type III minimum', '5.2', 2, 'Directional arrows for pedestrian guidance per SDM wayfinding standards.'),
    ('Dashed Line (Driveway)', 'yellow', '#FFFF00', 'Type II', '5.3', 3, 'Yellow dashed lines at driveway edges to delineate accessible routes.'),
    ('Solid Line (Curb Cut)', 'white', '#FFFFFF', 'Type III minimum', '5.4', 2, 'White solid lines marking curb cut boundaries and accessible route edges.'),
    ('Corner Box', 'white', '#FFFFFF', 'Type III minimum', '5.5', 2, 'Corner boxes at pedestrian refuge areas with enhanced reflectivity.'),
    ('Loading Zone Marking', 'white', '#FFFFFF', 'Type II', '5.6', 3, 'Standard loading zone boundary markings per SDM specifications.'),
    ('Bike Lane Marking', 'white', '#FFFFFF', 'Type III minimum', '5.7', 2, 'Protected bike lane markings integrated with sidewalk design.')
ON CONFLICT (marking_type) DO NOTHING;

-- =============================================================================
-- dim_surface_treatments: Color surface treatments from SDM Section 4.9
-- =============================================================================
-- Codifies colored surface treatments with performance specifications
CREATE TABLE IF NOT EXISTS dim_surface_treatments (
    treatment_id SERIAL PRIMARY KEY,
    treatment_name VARCHAR(128) NOT NULL UNIQUE,
    color_hex VARCHAR(7) NOT NULL,
    -- Hex color code per SDM specification
    permeability VARCHAR(32),
    -- Permeability level: impermeable, semi-permeable, permeable
    heat_reflection_index DECIMAL(5, 2),
    -- Solar reflectance index (0-100) per ASTM E1980
    stain_resistance VARCHAR(32),
    -- Resistance to staining: high, medium, low
    durability_rating VARCHAR(32),
    -- Expected performance rating: excellent, good, fair
    sdm_reference VARCHAR(16),
    -- SDM Section 4.9 reference
    maintenance_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert color surface treatments from SDM Section 4.9
INSERT INTO dim_surface_treatments
    (treatment_name, color_hex, permeability, heat_reflection_index, stain_resistance, durability_rating, sdm_reference, maintenance_notes)
VALUES
    ('NYC Red (Standard)', '#C41E3A', 'impermeable', 25.50, 'medium', 'good', '4.9', 
     'Standard red asphalt per NYC DOT specification. Requires refreshing every 3 years.'),
    ('NYC Green (Cool Pavement)', '#2D8659', 'semi-permeable', 42.00, 'medium', 'good', '4.9',
     'Green-colored permeable asphalt with high solar reflectance. Reduces heat island effect.'),
    ('Traffic Calming Yellow', '#FFD700', 'impermeable', 65.00, 'low', 'fair', '4.9',
     'High-visibility yellow for traffic calming zones. Requires more frequent repainting.'),
    ('Historic Blue (Landmark Districts)', '#004B87', 'impermeable', 15.00, 'high', 'excellent', '4.9',
     'Heritage blue color for historic district preservation. Premium durability treatment.'),
    ('Accessibility Yellow (Tactile)', '#FFE135', 'semi-permeable', 60.00, 'medium', 'good', '4.9',
     'High-contrast yellow for curb cuts and accessible route demarcation.')
ON CONFLICT (treatment_name) DO NOTHING;

-- =============================================================================
-- dim_defect_types: Sidewalk defect classifications tied to materials
-- =============================================================================
-- Codifies defect taxonomy with severity levels and material applicability
CREATE TABLE IF NOT EXISTS dim_defect_types (
    defect_id SERIAL PRIMARY KEY,
    defect_name VARCHAR(128) NOT NULL UNIQUE,
    -- Defect name (e.g., "Potholes", "Cracking", "Heaving")
    defect_category VARCHAR(64) NOT NULL,
    -- Category: surface_damage, structural, drainage, accessibility
    severity_level VARCHAR(32) NOT NULL,
    -- minor | moderate | severe | hazardous
    hazard_type VARCHAR(64),
    -- Trip hazard, drainage issue, water infiltration, structural
    typical_causes TEXT,
    -- Common causes (e.g., "water infiltration", "traffic loading")
    material_applicability VARCHAR(256),
    -- JSON or comma-separated materials affected: asphalt, concrete, pavers, etc.
    repair_urgency_days INT,
    -- Days before repair required by severity
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert defect taxonomy
INSERT INTO dim_defect_types
    (defect_name, defect_category, severity_level, hazard_type, typical_causes, material_applicability, repair_urgency_days, description)
VALUES
    ('Potholes', 'surface_damage', 'severe', 'trip_hazard', 'Water infiltration, traffic loading, freeze-thaw cycles', 'asphalt,SMA,OGFC', 30,
     'Surface depressions exposing aggregate or base. Severe trip/fall hazard requiring immediate repair.'),
    ('Linear Cracking', 'surface_damage', 'moderate', 'water_infiltration', 'Thermal stress, traffic loading, shrinkage', 'concrete,PCC,reinforced_concrete', 90,
     'Cracks >1/8 inch width allowing water infiltration. Non-hazardous but requires sealed repair.'),
    ('Alligator Cracking', 'surface_damage', 'severe', 'water_infiltration', 'Base failure, subgrade settlement', 'asphalt,SMA', 60,
     'Interconnected crack pattern indicating imminent failure. Requires complete section replacement.'),
    ('Spalling', 'surface_damage', 'moderate', 'trip_hazard', 'Freeze-thaw, salt exposure, poor curing', 'concrete,PCC,decorative_concrete', 90,
     'Flaking or chipping of surface layer. Potential trip hazard requiring patching or replacement.'),
    ('Heaving/Settlement', 'structural', 'hazardous', 'trip_hazard', 'Subgrade instability, tree root pressure, soil settlement', 'concrete,PCC,reinforced_concrete,pavers', 14,
     'Vertical displacement >1/2 inch between sections. Critical trip hazard requiring urgent repair.'),
    ('Rutting', 'surface_damage', 'moderate', 'drainage_issue', 'Traffic loading, soft asphalt base', 'asphalt,SMA,OGFC', 120,
     'Longitudinal depression from traffic wear. Affects drainage and pedestrian safety.'),
    ('Loose Pavers', 'surface_damage', 'moderate', 'trip_hazard', 'Base settlement, inadequate joint support', 'pavers,granite,vitreous_tile', 60,
     'Individual units rocking or displaced. Requires resetting or replacement.'),
    ('Drainage Blockage', 'drainage', 'moderate', 'water_pooling', 'Debris accumulation, sediment buildup', 'permeable_surfaces,pervious_concrete', 45,
     'Surface drainage outlets clogged preventing water infiltration. Requires cleaning/unclogging.'),
    ('Accessible Route Gap', 'accessibility', 'hazardous', 'trip_hazard', 'Maintenance deferral, material degradation', 'all', 7,
     'Gap or level change ≥1/4 inch in accessible route. ADA violation requiring immediate attention.'),
    ('Faded Markings', 'surface_damage', 'minor', 'visibility_issue', 'UV exposure, traffic wear', 'all', 180,
     'Markings faded below reflectivity minimum per SDM Section 5. Requires repainting within maintenance cycle.')
ON CONFLICT (defect_name) DO NOTHING;

-- =============================================================================
-- dim_ada_compliance: ADA accessibility requirements mapped to infrastructure
-- =============================================================================
-- Codifies ADA compliance requirements with material-aware applicability
CREATE TABLE IF NOT EXISTS dim_ada_compliance (
    compliance_id SERIAL PRIMARY KEY,
    requirement_id VARCHAR(32) NOT NULL UNIQUE,
    -- ID: ADA-1.0.1, ADA-2.1.2, etc. (ADA Accessibility Guidelines section)
    requirement_description TEXT NOT NULL,
    compliance_standard VARCHAR(256),
    -- Specific standard (e.g., "slope ≤1:20")
    sdm_reference VARCHAR(16),
    -- NYC Street Design Manual cross-reference
    applicable_to_materials VARCHAR(256),
    -- Materials or "all" if universal
    measurement_unit VARCHAR(64),
    -- Unit of measurement: percent, slope_ratio, inches, feet
    target_compliance_threshold DECIMAL(10, 4),
    -- Target threshold for compliance scoring
    enforcement_body VARCHAR(64),
    -- Enforcing authority: ADA, NYC DOT, FDNY, etc.
    violation_penalty VARCHAR(256),
    -- Typical penalty or enforcement action
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert ADA compliance requirements
INSERT INTO dim_ada_compliance
    (requirement_id, requirement_description, compliance_standard, sdm_reference, applicable_to_materials, measurement_unit, target_compliance_threshold, enforcement_body, violation_penalty, description)
VALUES
    ('ADA-4.3.1', 'Clear Pedestrian Path', 'Clear width minimum 5 feet', 'Section 2', 'all', 'feet', 5.0, 'ADA', 'NYC Dept of Justice violation notice',
     'Sidewalk must provide continuous clear pedestrian path of at least 5 feet width unobstructed by utilities, street furniture, or defects.'),
    ('ADA-4.3.2', 'Accessible Route Slope', 'Running slope ≤1:20 (5%)', 'Section 2', 'all', 'slope_ratio', 5.0, 'ADA', 'Repair order issued',
     'Cross-slope and running slope must not exceed 1:20 grade per ADA standards to ensure wheelchair accessibility.'),
    ('ADA-4.3.3', 'Level Changes', 'Level changes ≤1/4 inch beveled or ≤1/2 inch vertical', 'Section 2', 'all', 'inches', 0.5, 'ADA', 'Repair order issued',
     'Vertical discontinuities must be either beveled (<1:2 slope) or ≤1/2 inch to prevent trip/fall hazards.'),
    ('ADA-4.3.4', 'Surface Quality', 'Firm, stable, slip-resistant surface', 'Section 4', 'all', 'percent', 100.0, 'NYC DOT', 'Defect citation',
     'All surfaces must be firm (not soft), stable (not moving), and slip-resistant to accommodate mobility aids.'),
    ('ADA-4.3.5', 'Tactile Warning Strip', 'Detectability at curb ramps', 'Section 3', 'all', 'percent', 100.0, 'ADA', 'Repair order issued',
     'All curb ramps must have 24-inch deep truncated dome tactile warning strips detectable with cane.'),
    ('ADA-4.5.1', 'Curb Ramp Width', 'Minimum 4 feet clear width', 'Section 3', 'all', 'feet', 4.0, 'NYC DOT', 'Repair order issued',
     'Curb ramps must provide minimum 4-foot clear width (excluding flares) with maximum 1:8 slope.'),
    ('ADA-4.5.2', 'Curb Ramp Slope', 'Running slope ≤1:12 (8.33%), cross-slope ≤1:48', 'Section 3', 'all', 'slope_ratio', 8.33, 'NYC DOT', 'Repair order issued',
     'Curb ramp slopes must not exceed 1:12 running (1:8 maximum) with cross-slope ≤1:48 for drainage.'),
    ('ADA-4.7.1', 'Texture/Finish', 'Slip resistance coefficient >0.5 (ASTM D2047)', 'Section 4', 'all', 'percent', 100.0, 'NYC DOT', 'Repair order issued',
     'All sidewalk surfaces must maintain slip resistance coefficient >0.5 per ASTM D2047 wet pendulum test.')
ON CONFLICT (requirement_id) DO NOTHING;

-- =============================================================================
-- dim_contractor_type: Contractor classifications for repair work
-- =============================================================================
-- Codifies contractor types, certifications, and material specializations
CREATE TABLE IF NOT EXISTS dim_contractor_type (
    contractor_type_id SERIAL PRIMARY KEY,
    contractor_category VARCHAR(64) NOT NULL UNIQUE,
    -- Category: general_contractor, specialty_asphalt, concrete_specialist, accessible_design, etc.
    required_certifications VARCHAR(256),
    -- Required licenses/certs: NYC CHAR, DOT registration, OSHA, insurance
    specialized_materials VARCHAR(256),
    -- Materials they specialize in: asphalt, concrete, permeable_surfaces, historic
    minimum_bonding_amount INT,
    -- Minimum performance/payment bond requirement in dollars
    quality_assurance_requirement VARCHAR(256),
    -- QA requirements: third-party testing, inspection frequency, etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert contractor classifications
INSERT INTO dim_contractor_type
    (contractor_category, required_certifications, specialized_materials, minimum_bonding_amount, quality_assurance_requirement, description)
VALUES
    ('General Sidewalk Contractor', 'NYC CHAR, DOT registration, OSHA 30, liability insurance', 'asphalt,concrete,basic_repair', 250000, 
     'Third-party inspection at 25%, 50%, final. Video documentation of all work.',
     'Qualified for standard asphalt and concrete sidewalk repair projects per SDM standards.'),
    ('Specialty Asphalt Contractor', 'NYC CHAR, asphalt paving certification, DOT registration', 'asphalt,SMA,OGFC,color_treatments', 500000,
     'Full-depth core testing, plant certifications, daily quality testing (Marshall stability, gradation).',
     'Specialized in hot-mix and specialty asphalt per SDM Sections 4.1-4.3. Performs material certification.'),
    ('Concrete Specialist', 'NYC CHAR, concrete contractor license, ACI certification', 'concrete,PCC,reinforced_concrete,decorative', 500000,
     'Mix design approval, strength testing (compressive strength at 7, 28 days), surface finish inspection.',
     'Specialized in Portland cement concrete per SDM Sections 4.4-4.6. ACI member required.'),
    ('Permeable Surface Expert', 'NYC CHAR, permeable pavement certification, drainage engineer', 'permeable_surfaces,pervious_concrete,pavers', 350000,
     'Permeability testing post-construction, base preparation verification, infiltration rate monitoring.',
     'Specialized in stormwater management and permeable surfaces per SDM Section 4.7. Environmental compliance focus.'),
    ('Historic Preservation Contractor', 'NYC CHAR, historic district specialist, master craftsperson', 'granite,historic_materials,vitreous_tile', 350000,
     'Material matching certification, craft technique documentation, preservation council approval required.',
     'Specialized in historic sidewalk materials per SDM Section 4.8. Requires preservation board training.'),
    ('Accessible Design Contractor', 'NYC CHAR, ADA compliance specialist, accessible design certification', 'all', 250000,
     'Curb ramp audit, slope/level verification, tactile strip inspection, full ADA compliance documentation.',
     'Specialized in ADA compliance and accessible route remediation per NYC DOT ADA standards.'),
    ('Color Treatment Specialist', 'NYC CHAR, colored asphalt certification, traffic management', 'color_treatments,distinctive_surfaces', 200000,
     'Color specification matching, reflectivity verification (ASTM D2035), application uniformity inspection.',
     'Specialized in colored surface treatments per SDM Section 4.9. Reflectivity and durability specialists.')
ON CONFLICT (contractor_category) DO NOTHING;

-- =============================================================================
-- Indexing for performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_dim_materials_category ON dim_materials(material_category);
CREATE INDEX IF NOT EXISTS idx_dim_materials_sdm_section ON dim_materials(sdm_section);
CREATE INDEX IF NOT EXISTS idx_dim_pavement_markings_type ON dim_pavement_markings(marking_type);
CREATE INDEX IF NOT EXISTS idx_dim_defect_types_category ON dim_defect_types(defect_category);
CREATE INDEX IF NOT EXISTS idx_dim_defect_types_severity ON dim_defect_types(severity_level);
CREATE INDEX IF NOT EXISTS idx_dim_ada_compliance_requirement ON dim_ada_compliance(requirement_id);
CREATE INDEX IF NOT EXISTS idx_dim_contractor_type_category ON dim_contractor_type(contractor_category);

-- =============================================================================
-- Audit trail table for domain model changes
-- =============================================================================
CREATE TABLE IF NOT EXISTS domain_model_audit_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL,
    operation VARCHAR(16),
    -- INSERT, UPDATE, DELETE
    record_id INT,
    changed_fields JSONB,
    changed_by VARCHAR(128),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Grant default privileges for toolkit user (if exists)
-- =============================================================================
-- Uncomment and adjust owner if needed for production
-- ALTER TABLE dim_materials OWNER TO toolkit_user;
-- ALTER TABLE dim_pavement_markings OWNER TO toolkit_user;
-- ALTER TABLE dim_surface_treatments OWNER TO toolkit_user;
-- ALTER TABLE dim_defect_types OWNER TO toolkit_user;
-- ALTER TABLE dim_ada_compliance OWNER TO toolkit_user;
-- ALTER TABLE dim_contractor_type OWNER TO toolkit_user;
-- ALTER TABLE domain_model_audit_log OWNER TO toolkit_user;
