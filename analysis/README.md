# Sidewalk EDA - analysis

Quickstart (Windows / PowerShell + conda recommended):

1) copy .env.template to .env and fill PG_DSN:
   Copy-Item .\.env.template .\.env

2) create conda env (recommended):
   conda create -n sidewalk python=3.11 -y
   conda activate sidewalk
   conda install -c conda-forge jupyterlab jupytext python-dotenv plotly pandas sqlalchemy geopandas scikit-learn rpy2 -y

3) open the notebook (Jupytext markdown -> ipynb):
   jupytext --to notebook analysis\sidewalk_eda.md
   jupyter lab analysis\sidewalk_eda.ipynb

4) produce an HTML report (optional):
   jupyter nbconvert --to html --execute analysis\sidewalk_eda.ipynb --output analysis\sidewalk_eda.html

Notes:
- Geo exports require geopandas; R models require R packages (brms, rstanarm, cmdstanr).
