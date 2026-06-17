import duckdb

con = duckdb.connect('md:')
res = con.sql("SELECT * FROM MD_GET_DIVE('49ad6d47-c9e1-45e2-b512-cbfea43a521e')").df()
print(res.columns)
print(res['content'].iloc[0] if 'content' in res.columns else res['source'].iloc[0] if 'source' in res.columns else res.head())