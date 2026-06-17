import duckdb
import pandas as pd
pd.set_option('display.max_rows', None)

con = duckdb.connect('md:')
res = con.sql("""
    SELECT schema, name 
    FROM (SHOW ALL TABLES) 
    WHERE database = 'nyc_mission_control'
""").df()
print(res)
