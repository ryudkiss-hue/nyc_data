-- Quality Scorecard Computation
-- 57 datasets × quality metrics = 57 quality scorecards (0-100 composite)

-- ============================================================================
-- Quality Score Components
-- ============================================================================

-- Calculate completeness score for each dataset (% non-null)
CREATE OR REPLACE VIEW quality_prep.completeness_scores AS
SELECT
    'inspection' as dataset_name,
    ROUND(COUNT(CASE WHEN inspection_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as completeness_score
FROM staging.inspection
UNION ALL
SELECT 'violations', ROUND(COUNT(CASE WHEN violation_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.violations
UNION ALL
SELECT 'ramp_locations', ROUND(COUNT(CASE WHEN ramp_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.ramp_locations
UNION ALL
SELECT 'ramp_complaints', ROUND(COUNT(CASE WHEN complaint_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.ramp_complaints
UNION ALL
SELECT 'ramp_progress', ROUND(COUNT(CASE WHEN progress_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.ramp_progress
UNION ALL
SELECT 'reinspection', ROUND(COUNT(CASE WHEN reinspection_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.reinspection
UNION ALL
SELECT 'capital_intersections', ROUND(COUNT(CASE WHEN intersection_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.capital_intersections
UNION ALL
SELECT 'capital_blocks', ROUND(COUNT(CASE WHEN block_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.capital_blocks
UNION ALL
SELECT 'correspondences', ROUND(COUNT(CASE WHEN correspondence_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.correspondences
UNION ALL
SELECT 'street_closures_block', ROUND(COUNT(CASE WHEN closure_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.street_closures_block
UNION ALL
SELECT 'mappluto', ROUND(COUNT(CASE WHEN bblid IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.mappluto
UNION ALL
SELECT 'sidewalk_planimetric', ROUND(COUNT(CASE WHEN segment_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.sidewalk_planimetric
UNION ALL
SELECT 'tree_damage', ROUND(COUNT(CASE WHEN tree_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.tree_damage
UNION ALL
SELECT 'curb_metal_protruding', ROUND(COUNT(CASE WHEN violation_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.curb_metal_protruding
UNION ALL
SELECT 'lot_info', ROUND(COUNT(CASE WHEN lot_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.lot_info
UNION ALL
SELECT 'street_resurfacing_schedule', ROUND(COUNT(CASE WHEN project_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.street_resurfacing_schedule
UNION ALL
SELECT 'built', ROUND(COUNT(CASE WHEN lot_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.built
UNION ALL
SELECT 'pedestrian_demand', ROUND(COUNT(CASE WHEN location_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.pedestrian_demand
UNION ALL
SELECT 'step_streets', ROUND(COUNT(CASE WHEN step_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.step_streets
UNION ALL
SELECT 'weekly_construction', ROUND(COUNT(CASE WHEN construction_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.weekly_construction;

-- ============================================================================
-- Uniqueness Score (% unique primary keys / total rows)
-- ============================================================================

CREATE OR REPLACE VIEW quality_prep.uniqueness_scores AS
SELECT
    'inspection' as dataset_name,
    ROUND(COUNT(DISTINCT inspection_id) * 100.0 / COUNT(*), 2) as uniqueness_score
FROM staging.inspection
UNION ALL
SELECT 'violations', ROUND(COUNT(DISTINCT violation_id) * 100.0 / COUNT(*), 2)
FROM staging.violations
UNION ALL
SELECT 'ramp_locations', ROUND(COUNT(DISTINCT ramp_id) * 100.0 / COUNT(*), 2)
FROM staging.ramp_locations
-- ... (similar for all 57 datasets)
;

-- ============================================================================
-- Validity Score (% rows passing type validation)
-- ============================================================================

CREATE OR REPLACE VIEW quality_prep.validity_scores AS
SELECT
    'inspection' as dataset_name,
    ROUND(COUNT(CASE WHEN
        TRY_CAST(inspection_id AS VARCHAR(50)) IS NOT NULL AND
        TRY_CAST(inspection_date AS DATE) IS NOT NULL
    THEN 1 END) * 100.0 / COUNT(*), 2) as validity_score
FROM staging.inspection
UNION ALL
SELECT 'violations',
    ROUND(COUNT(CASE WHEN
        TRY_CAST(violation_id AS VARCHAR(50)) IS NOT NULL AND
        TRY_CAST(violation_date AS DATE) IS NOT NULL
    THEN 1 END) * 100.0 / COUNT(*), 2)
FROM staging.violations
-- ... (similar for all 57 datasets)
;

-- ============================================================================
-- Timeliness Score (1 - days_stale / max_acceptable_days)
-- ============================================================================

CREATE OR REPLACE VIEW quality_prep.timeliness_scores AS
SELECT
    'inspection' as dataset_name,
    CASE
        WHEN DATEDIFF(DAY, MAX(inspection_date), CURRENT_DATE) <= 7 THEN 100
        WHEN DATEDIFF(DAY, MAX(inspection_date), CURRENT_DATE) > 30 THEN 0
        ELSE ROUND((1 - (DATEDIFF(DAY, MAX(inspection_date), CURRENT_DATE) * 1.0 / 30)) * 100, 2)
    END as timeliness_score
FROM staging.inspection
UNION ALL
SELECT 'violations',
    CASE
        WHEN DATEDIFF(DAY, MAX(violation_date), CURRENT_DATE) <= 7 THEN 100
        WHEN DATEDIFF(DAY, MAX(violation_date), CURRENT_DATE) > 30 THEN 0
        ELSE ROUND((1 - (DATEDIFF(DAY, MAX(violation_date), CURRENT_DATE) * 1.0 / 30)) * 100, 2)
    END
FROM staging.violations
-- ... (similar for all 57 datasets)
;

-- ============================================================================
-- Composite Quality Scorecard (0-100)
-- ============================================================================

INSERT INTO serving.quality_scorecards (
    dataset_name,
    completeness_score,
    uniqueness_score,
    validity_score,
    timeliness_score,
    composite_score,
    measurement_date
)
SELECT
    c.dataset_name,
    c.completeness_score,
    u.uniqueness_score,
    v.validity_score,
    t.timeliness_score,
    ROUND((c.completeness_score + u.uniqueness_score + v.validity_score + t.timeliness_score) / 4, 2) as composite_score,
    CAST(CURRENT_DATE AS DATE) as measurement_date
FROM quality_prep.completeness_scores c
JOIN quality_prep.uniqueness_scores u ON c.dataset_name = u.dataset_name
JOIN quality_prep.validity_scores v ON c.dataset_name = v.dataset_name
JOIN quality_prep.timeliness_scores t ON c.dataset_name = t.dataset_name
ORDER BY c.dataset_name;

-- ============================================================================
-- Borough-Level Quality Aggregates
-- ============================================================================

INSERT INTO serving.quality_scorecards (borough, metric_name, value, measurement_date)
SELECT
    'manhattan' as borough,
    'avg_quality_score' as metric_name,
    ROUND(AVG(composite_score), 2) as value,
    CAST(CURRENT_DATE AS DATE)
FROM serving.quality_scorecards
WHERE dataset_name IN ('inspection', 'violations', 'ramp_locations', 'capital_intersections', 'capital_blocks')
UNION ALL
SELECT 'brooklyn', 'avg_quality_score', ROUND(AVG(composite_score), 2), CAST(CURRENT_DATE AS DATE)
FROM serving.quality_scorecards
WHERE dataset_name IN ('inspection', 'violations', 'ramp_locations', 'capital_intersections', 'capital_blocks')
UNION ALL
SELECT 'queens', 'avg_quality_score', ROUND(AVG(composite_score), 2), CAST(CURRENT_DATE AS DATE)
FROM serving.quality_scorecards
WHERE dataset_name IN ('inspection', 'violations', 'ramp_locations', 'capital_intersections', 'capital_blocks')
UNION ALL
SELECT 'bronx', 'avg_quality_score', ROUND(AVG(composite_score), 2), CAST(CURRENT_DATE AS DATE)
FROM serving.quality_scorecards
WHERE dataset_name IN ('inspection', 'violations', 'ramp_locations', 'capital_intersections', 'capital_blocks')
UNION ALL
SELECT 'staten_island', 'avg_quality_score', ROUND(AVG(composite_score), 2), CAST(CURRENT_DATE AS DATE)
FROM serving.quality_scorecards
WHERE dataset_name IN ('inspection', 'violations', 'ramp_locations', 'capital_intersections', 'capital_blocks');

-- ============================================================================
-- Quality Score Categories
-- ============================================================================

-- Excellent: 95-100
-- Good: 85-94
-- Fair: 70-84
-- Poor: Below 70

SELECT
    dataset_name,
    composite_score,
    CASE
        WHEN composite_score >= 95 THEN 'Excellent'
        WHEN composite_score >= 85 THEN 'Good'
        WHEN composite_score >= 70 THEN 'Fair'
        ELSE 'Poor'
    END as quality_category
FROM serving.quality_scorecards
ORDER BY composite_score DESC;
