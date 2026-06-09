import dash
from dash import html
import uvicorn
from fastapi import FastAPI

dash_app = dash.Dash(__name__)
dash_app.layout = html.Div("Minimal Test OK")

app = FastAPI()
# Manual mount to test
from dash.middleware import DispatcherMiddleware
from starlette.middleware.wsgi import WSGIMiddleware

# This is usually how you'd mount a WSGI Dash app in FastAPI
# but DashProxy with backend="fastapi" does it differently.

if __name__ == "__main__":
    dash_app.run(port=8012, debug=True)
