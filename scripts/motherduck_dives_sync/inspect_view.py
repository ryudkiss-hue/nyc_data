import duckdb
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("MOTHERDUCK_TOKEN")

con = duckdb.connect(f"md:?motherduck_token={token}")

print("--- DESCRIBE v_metric_dashboard ---")
try:
    res = con.execute("DESCRIBE nyc_mission_control.app_queries.v_metric_dashboard").df()
    print(res)
    
    print("\n--- VIEW DEFINITION ---")
    sql = con.execute("""
        SELECT sql 
        FROM nyc_mission_control.information_schema.views 
        WHERE table_schema = 'app_queries' AND table_name = 'v_metric_dashboard'
    """).fetchone()[0]
    print(sql)
except Exception as e:
    print(f"Error: {e}")