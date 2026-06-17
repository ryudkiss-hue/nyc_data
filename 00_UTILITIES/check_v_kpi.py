import duckdb
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

con = duckdb.connect('md:')
res = con.sql("SELECT * FROM nyc_mission_control.app_queries.v_kpi_dashboard LIMIT 10").df()
print(res)

print("\nUnique KPI Names:")
print(con.sql("SELECT DISTINCT kpi_name FROM nyc_mission_control.app_queries.v_kpi_dashboard").df())