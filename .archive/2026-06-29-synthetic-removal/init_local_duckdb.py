import os
import duckdb
from dotenv import load_dotenv

def init_db():
    load_dotenv()
    db_path = os.getenv("DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb")
    print(f"Initializing database at: {db_path}")
    con = duckdb.connect(db_path)
    
    con.execute("CREATE SCHEMA IF NOT EXISTS app_queries")
    
    # 1. v_metric_dashboard
    # Generate rows for ALL boroughs (MN, BK, BX, QN, SI) + 'ALL' fallback
    con.execute("DROP VIEW IF EXISTS app_queries.v_metric_dashboard")
    
    metrics = [
        ('total_inspections', 'Total Inspections', 12543.0, 5.2, 'Inspection Performance'),
        ('inspection_rate', 'Inspection Rate', 450.0, 1.2, 'Inspection Performance'),
        ('avg_violations_per_inspection', 'Avg Violations', 2.3, -0.5, 'Inspection Performance'),
        ('critical_violations', 'Critical Violations', 123.0, -10.5, 'Inspection Performance'),
        ('inspection_backlog', 'Inspection Backlog', 14.0, 2.1, 'Inspection Performance'),
        
        ('data_completeness', 'Data Completeness', 98.5, 0.2, 'Quality Metrics'),
        ('data_validity', 'Data Validity', 97.2, 1.1, 'Quality Metrics'),
        ('data_consistency', 'Data Consistency', 99.1, 0.0, 'Quality Metrics'),
        ('data_freshness', 'Data Freshness', 1.5, -0.5, 'Quality Metrics'),
        ('quality_score', 'Overall Quality', 96.5, 0.4, 'Quality Metrics'),
        
        ('ramp_completion_rate', 'Ramp Completion', 75.4, 3.2, 'Ramp Accessibility'),
        ('ramp_complaints', 'Ramp Complaints', 45.0, -12.0, 'Ramp Accessibility'),
        ('ramp_progress_month', 'Progress This Month', 120.0, 15.0, 'Ramp Accessibility'),
        ('ramp_sla_breach', 'SLA Breach Risk', 5.2, -1.0, 'Ramp Accessibility'),
        
        ('morans_i_statistic', "Moran's I", 0.45, 0.05, 'Spatial Patterns'),
        ('spatial_clusters', 'Spatial Clusters', 12.0, 0.0, 'Spatial Patterns'),
        ('hotspot_concentration', 'Hotspot Concentration', 45.2, -2.1, 'Spatial Patterns'),
        ('outlier_count', 'Anomaly Count', 34.0, 5.0, 'Spatial Patterns')
    ]
    
    view_sql = "CREATE VIEW app_queries.v_metric_dashboard AS "
    union_parts = []
    for b in ['ALL', 'MN', 'BK', 'BX', 'QN', 'SI']:
        for m_id, m_name, val, chg, cat in metrics:
            # Let's add slight variations per borough for realism
            b_val = val
            if b != 'ALL':
                # Deterministic seed/variation based on borough
                h = sum(ord(c) for c in b)
                b_val = val * (0.85 + (h % 30) / 100.0)
            escaped_m_name = m_name.replace("'", "''")
            union_parts.append(
                f"SELECT '{m_id}' AS metric_id, '{escaped_m_name}' AS metric_name, '{b}' AS borough, "
                f"{b_val:.2f} AS value, {chg:.2f} AS change_pct, '{cat}' AS category"
            )
    view_sql += " UNION ALL ".join(union_parts)
    con.execute(view_sql)
    
    # 2. v_phase_b_results
    con.execute("DROP VIEW IF EXISTS app_queries.v_phase_b_results")
    b_parts = []
    for b in ['ALL', 'MN', 'BK', 'BX', 'QN', 'SI']:
        val = 0.45 if b == 'ALL' else 0.45 - (len(b)*0.03)
        b_parts.append(
            f"SELECT '{b}' AS borough, {val:.3f} AS morans_i_value, 'Cluster' AS classification, "
            f"12 AS location_count, 0.01 AS p_value, 0.01 AS significance, '2026-06-28 12:00:00' AS analytics_timestamp"
        )
    con.execute("CREATE VIEW app_queries.v_phase_b_results AS " + " UNION ALL ".join(b_parts))
    
    # 3. v_phase_c_results
    con.execute("DROP VIEW IF EXISTS app_queries.v_phase_c_results")
    c_parts = []
    for b in ['ALL', 'MN', 'BK', 'BX', 'QN', 'SI']:
        skew = 0.12 if b == 'ALL' else 0.12 + (len(b)*0.02)
        c_parts.append(
            f"SELECT '{b}' AS borough, 1200 AS record_count, 45.2 AS mean_val, 42.1 AS median_val, "
            f"15.3 AS std_val, {skew:.3f} AS skewness, 'NORMAL' AS distribution_type, "
            f"95.0 AS concentration_percent, '2026-06-28 12:00:00' AS analytics_timestamp"
        )
    con.execute("CREATE VIEW app_queries.v_phase_c_results AS " + " UNION ALL ".join(c_parts))
    
    # 4. v_phase_d_results
    con.execute("DROP VIEW IF EXISTS app_queries.v_phase_d_results")
    d_parts = []
    # Add multiple outlier points across boroughs
    outliers = [
        ('LOC-01', 'MN', 40.7128, -74.0060, 15, 2.8, 'High-High', 1),
        ('LOC-02', 'BK', 40.6782, -73.9442, 22, 3.1, 'High-High', 2),
        ('LOC-03', 'BX', 40.8448, -73.8648, 8, 2.1, 'High-Low', 3),
        ('LOC-04', 'QN', 40.7282, -73.7949, 11, 2.5, 'Low-High', 4),
        ('LOC-05', 'SI', 40.5795, -74.1502, 5, 2.0, 'High-High', 5),
    ]
    for loc_id, b, lat, lon, count, z, o_cls, pri in outliers:
        d_parts.append(
            f"SELECT '{loc_id}' AS location_id, '{b}' AS borough, {lat:.6f} AS latitude, {lon:.6f} AS longitude, "
            f"{count} AS inspection_count, {z:.2f} AS z_score_violations, '{o_cls}' AS outlier_class, "
            f"{pri} AS priority_rank, '2026-06-28 12:00:00' AS analytics_timestamp"
        )
    con.execute("CREATE VIEW app_queries.v_phase_d_results AS " + " UNION ALL ".join(d_parts))
    
    # 5. v_phase_e_decomposition
    con.execute("DROP VIEW IF EXISTS app_queries.v_phase_e_decomposition")
    e_parts = []
    # Create time series data for last 12 months
    months = [
        "2025-07-01", "2025-08-01", "2025-09-01", "2025-10-01", "2025-11-01", "2025-12-01",
        "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01"
    ]
    for b in ['ALL', 'MN', 'BK', 'BX', 'QN', 'SI']:
        for idx, m_str in enumerate(months):
            trend = 100 + idx * 2.5
            seas = 10 * (idx % 4 - 1.5)
            res = (idx * 7) % 5 - 2
            v_cnt = trend + seas + res
            fc = trend + seas
            e_parts.append(
                f"SELECT '{m_str}' AS date, '{b}' AS borough, {v_cnt:.2f} AS violation_count, "
                f"{trend:.2f} AS trend_value, {seas:.2f} AS seasonal_value, {res:.2f} AS residual_value, "
                f"{fc:.2f} AS forecast_next_period, '2026-06-28 12:00:00' AS analytics_timestamp"
            )
    con.execute("CREATE VIEW app_queries.v_phase_e_decomposition AS " + " UNION ALL ".join(e_parts))
    
    # 6. v_phase_f_bootstrap_ci
    con.execute("DROP VIEW IF EXISTS app_queries.v_phase_f_bootstrap_ci")
    f_parts = []
    for b in ['ALL', 'MN', 'BK', 'BX', 'QN', 'SI']:
        f_parts.append(
            f"SELECT '{b}' AS borough, 95.0 AS point_estimate, 92.0 AS ci_lower_95, "
            f"98.0 AS ci_upper_95, 6.0 AS interval_width, 0.99 AS prob_meets_sla, "
            f"'LOW' AS risk_level, '2026-06-28 12:00:00' AS analytics_timestamp"
        )
    con.execute("CREATE VIEW app_queries.v_phase_f_bootstrap_ci AS " + " UNION ALL ".join(f_parts))
    
    con.close()
    print("Successfully initialized local DuckDB with app_queries schema and comprehensive visualization views!")

if __name__ == "__main__":
    init_db()
