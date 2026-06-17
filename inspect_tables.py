import duckdb
import pandas as pd
pd.set_option('display.max_rows', None)

con = duckdb.connect('md:')

for table in ['inspection', 'violations', 'dismissals']:
    print(f"\n--- Columns in {table} ---")
    res = con.sql(f"DESCRIBE nyc_mission_control.main.{table}").df()
    print(res[['column_name', 'column_type']])