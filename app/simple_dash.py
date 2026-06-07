import dash
from dash import html

app = dash.Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1("Industrial Dash - Final Isolation Test", style={"color": "black"}),
        html.P("If you see this, the environment is working correctly.", style={"color": "black"}),
    ],
    style={"padding": "100px", "backgroundColor": "white", "minHeight": "100vh"}
)

if __name__ == "__main__":
    app.run(debug=False, port=8070)
