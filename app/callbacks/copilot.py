"""Copilot callbacks — wired to real Anthropic API (claude-haiku-4-5)."""
import logging
import os

import dash_mantine_components as dmc
from dash import Input, Output, State, no_update

logger = logging.getLogger(__name__)

_SIM_SYSTEM_PROMPT = (
    "You are a NYC DOT SIM (Sidewalk Inspection Management) AI analyst. "
    "You have access to a 5.7 GB warehouse of 117+ datasets covering sidewalk inspections, "
    "violations, contractor repairs, ADA ramp complaints, capital projects, and 311 complaints. "
    "You answer analytical questions from SIM Project Analysts precisely and concisely. "
    "When referencing data, cite specific KPIs, borough differences, or trends where relevant. "
    "Do not fabricate statistics."
)


def _call_anthropic(user_text: str, model: str, history_text: str = "") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "ANTHROPIC_API_KEY not set. Set it in your environment to enable AI responses. "
            "For now: ask about inspection trends, violation counts, ADA ramp compliance, "
            "or capital budget burn rates — I can answer from the warehouse once the key is configured."
        )
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        messages = []
        if history_text:
            messages.append({"role": "user", "content": f"Prior context:\n{history_text}"})
            messages.append({"role": "assistant", "content": "Understood."})
        messages.append({"role": "user", "content": user_text})
        resp = client.messages.create(
            model=model or "claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SIM_SYSTEM_PROMPT,
            messages=messages,
        )
        return resp.content[0].text if resp.content else "No response generated."
    except Exception as e:
        logger.error(f"Anthropic API error: {e}", exc_info=True)
        return f"API error: {str(e)[:200]}"


def register_copilot_callbacks(app):
    @app.callback(
        Output("copilot-history", "children"),
        Input("btn-copilot-send", "n_clicks"),
        [
            State("copilot-input", "value"),
            State("copilot-history", "children"),
            State("llm-model-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def update_copilot_chat(n_clicks, user_text, history, model):
        if not user_text:
            return no_update
        if history is None:
            history = []

        # Summarize prior conversation for context window
        prior_text = " | ".join(
            str(m.get("props", {}).get("children", "")) for m in history[-6:]
            if isinstance(m, dict)
        )

        model_id = model or "claude-haiku-4-5-20251001"
        bot_reply = _call_anthropic(user_text, model_id, prior_text)

        history.append(dmc.Alert(user_text, title="You", color="gray", mt="xs"))
        history.append(dmc.Alert(bot_reply, title="SIM AI Analyst", color="blue", mt="xs"))
        return history
