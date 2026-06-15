"""Interactive components for Dash app."""


def param_slider(
    label=None, min_val=0, max_val=100, step=1, value=50, slider_id=None, aria_label=None, **kwargs
):
    """Create a parameter slider component."""
    return {
        "type": "slider",
        "label": label,
        "min": min_val,
        "max": max_val,
        "step": step,
        "value": value,
        "id": slider_id,
        "aria_label": aria_label or label,
    }


def tip_card(title, content, id=None, **kwargs):
    """Create a tip card component."""
    return {"type": "card", "title": title, "content": content, "id": id}


__all__ = ["param_slider", "tip_card"]
