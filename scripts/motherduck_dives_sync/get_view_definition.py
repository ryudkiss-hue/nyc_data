import duckdb
import os

con = duckdb.connect('md:nyc_mission_control')

try:
    print("--- VIEW DEFINITION ---")
    sql = con.execute("""
        SELECT sql 
        FROM information_schema.views 
        WHERE table_schema = 'app_queries' AND table_name = 'v_metric_dashboard'
    """).fetchone()[0]
    print(sql)
except Exception as e:
    print(f"Error: {e}")
