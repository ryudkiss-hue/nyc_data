import duckdb
con = duckdb.connect('md:')
df = con.sql("SELECT function_name, parameters, function_type FROM duckdb_functions() WHERE function_name LIKE '%MD_GET_DIVE%'").df()
print(df)
