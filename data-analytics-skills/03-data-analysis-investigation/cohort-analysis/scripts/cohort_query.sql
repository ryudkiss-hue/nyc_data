-- Cohort Analysis Base Query Template
-- Purpose: Produce one row per (user, cohort_period, activity_period) for retention analysis.
-- Adapt the table/column names to your schema, then run through cohort_builder.py or retention_matrix.py.

-- ============================================================
-- STEP 1: Define cohort membership (one row per user)
-- ============================================================
WITH cohort_membership AS (
    SELECT
        user_id,
        DATE_TRUNC('month', signup_date)  AS cohort_date  -- adjust granularity: 'week', 'day'
    FROM users
    WHERE
        signup_date >= '2023-01-01'     -- analysis start date
        AND is_test_account = FALSE      -- exclude internal/test accounts
),

-- ============================================================
-- STEP 2: Define activity events (what counts as "retained")
-- ============================================================
activity_events AS (
    SELECT
        user_id,
        DATE_TRUNC('month', event_date) AS activity_date  -- must match cohort_date granularity
    FROM user_events
    WHERE
        event_type = 'session_start'    -- CHANGE to your retention event
        AND event_date >= '2023-01-01'
),

-- ============================================================
-- STEP 3: Join cohorts to activity
-- ============================================================
cohort_activity AS (
    SELECT
        c.user_id,
        c.cohort_date,
        a.activity_date
    FROM cohort_membership c
    LEFT JOIN activity_events a
        ON c.user_id = a.user_id
        AND a.activity_date >= c.cohort_date  -- only count activity after joining
)

-- ============================================================
-- FINAL: Output for cohort_builder.py or retention_matrix.py
-- ============================================================
SELECT
    user_id,
    cohort_date,
    activity_date
FROM cohort_activity
WHERE activity_date IS NOT NULL
ORDER BY cohort_date, user_id, activity_date;

-- ============================================================
-- VARIANT: Revenue retention (instead of user retention)
-- Replace activity_events CTE with:
-- ============================================================
/*
activity_events AS (
    SELECT
        user_id,
        DATE_TRUNC('month', payment_date) AS activity_date,
        SUM(amount)                        AS period_revenue
    FROM payments
    WHERE status = 'succeeded'
    GROUP BY 1, 2
)
-- Then add period_revenue to the final SELECT and aggregate in retention_matrix.py
*/

-- ============================================================
-- VARIANT: Feature adoption cohort
-- Group users by when they first used a specific feature:
-- ============================================================
/*
cohort_membership AS (
    SELECT
        user_id,
        DATE_TRUNC('month', MIN(event_date)) AS cohort_date
    FROM user_events
    WHERE event_type = 'feature_x_used'
    GROUP BY user_id
)
*/
