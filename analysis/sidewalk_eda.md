# %% [markdown]
# NYC DOT Sidewalk EDA
This Jupytext markdown-first notebook contains discovery, QA, KPIs, spatial maps, time-series, and Bayesian templates.

# %%
# Setup: env, imports, connection helper
from dotenv import load_dotenv
load_dotenv('.env')
import os, logging
import pandas as pd
logging.basicConfig(level=logging.INFO)
from analysis import helpers
cfg = helpers.load_env()
PG_DSN = cfg.get('PG_DSN')
if not PG_DSN:
    raise SystemExit('Set PG_DSN in .env or update .env from .env.template')

# %%
# Connect (SQLAlchemy preferred)
engine = helpers.get_engine(PG_DSN)

# %% [markdown]
# Discovery: list candidate tables

# %%
tables = helpers.list_tables(engine)
display(tables.head(50))
candidates = helpers.candidate_sidewalk_tables(engine)
print('Candidate tables:', candidates)

# %% [markdown]
# Sample a table and quick QA

# %%
table = candidates[0] if candidates else None
df = helpers.safe_read_table(engine, table, limit=2000) if table else pd.DataFrame()
df.shape, df.columns.tolist()

# %%
df.info()
df.describe(include='all').T

# %% [markdown]
# KPIs (Python toolkit if available)

# %%
kpis = helpers.compute_kpis_from_df(df)
kpis

# %% [markdown]
# Spatial: detect lat/lon and plot (Plotly)

# %%
import plotly.express as px
latlon = helpers.find_latlon_columns(df)
if latlon:
    lat_col, lon_col = latlon
    mdf = df.dropna(subset=[lat_col, lon_col])
    if not mdf.empty:
        fig = px.scatter_mapbox(mdf, lat=lat_col, lon=lon_col, zoom=11, height=600, mapbox_style='open-street-map', title=f'{table} points')
        fig.show()
else:
    print('No lat/lon detected in sample.')

# %% [markdown]
# Time-series: monthly aggregation example

# %%
date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower() or 'created' in c.lower()]
if date_cols:
    dc = date_cols[0]
    df['_date_'] = pd.to_datetime(df[dc], errors='coerce')
    ts = df.dropna(subset=['_date_']).groupby(pd.Grouper(key='_date_', freq='M')).size().rename('count').reset_index()
    fig = px.line(ts, x='_date_', y='count', title=f'{table} - monthly events')
    fig.show()
else:
    print('No date-like column found.')

# %% [markdown]
# Clustering hotspots (optional) — requires scikit-learn

# %%
try:
    from sklearn.cluster import DBSCAN
    import numpy as np
    if latlon:
        coords = df[[lat_col, lon_col]].dropna()
        if not coords.empty:
            X = np.radians(coords[[lat_col, lon_col]].to_numpy())
            kms_per_radian = 6371.0088
            eps = 200 / 1000.0 / kms_per_radian
            db = DBSCAN(eps=eps, min_samples=5, metric='haversine').fit(X)
            coords['cluster'] = db.labels_
            fig = px.scatter_mapbox(coords, lat=lat_col, lon=lon_col, color='cluster', zoom=11, height=600, mapbox_style='open-street-map', title='Clusters')
            fig.show()
except Exception as e:
    print('Clustering skipped:', e)

# %% [markdown]
# R / Bayesian templates
# - To run R analysis inline install rpy2 and use %load_ext rpy2.ipython
# - Alternatively open an R-kernel notebook and run brms/rstanarm models

# %% [markdown]
# Export: save sample CSV
# %%
export_dir = cfg.get('EXPORT_DIR', 'analysis')
os.makedirs(export_dir, exist_ok=True)
sample_csv = os.path.join(export_dir, f'{table}_sample.csv')
df.to_csv(sample_csv, index=False)
print('Saved sample CSV:', sample_csv)
