import dash_mantine_components as dmc
from dash import Input, Output, State, callback, no_update


def register_copilot_callbacks(app):
    @app.callback(
        Output("copilot-history", "children"),
        Input("btn-copilot-send", "n_clicks"),
        [State("copilot-input", "value"),
         State("copilot-history", "children"),
         State("llm-model-select", "value")],
        prevent_initial_call=True
    )
    def update_copilot_chat(n_clicks, user_text, history, model):
        if not user_text: return no_update
        if history is None: history = []
        new_user_msg = dmc.Alert(user_text, title=f"You ({model})", color="gray", mt="xs")
        bot_reply = f"System analysis complete using {model}. Identified latent friction surge in Manhattan."
        new_bot_msg = dmc.Alert(bot_reply, title="SIM AI Analyst", color="blue", mt="xs")
        history.append(new_user_msg)
        history.append(new_bot_msg)
        return history
