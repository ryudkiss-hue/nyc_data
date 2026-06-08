import dash
import dash_mantine_components as dmc
from dash import html

app = dash.Dash(__name__)

app.layout = dmc.MantineProvider(
    children=[
        html.Div("Industrial Dash Test - OK", style={"color": "black", "fontSize": "24px", "padding": "50px"})
    ]
)

if __name__ == "__main__":
    app.run(debug=False, port=8055)
