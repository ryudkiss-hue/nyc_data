"""Interactive components for Dash app."""

def param_slider(min_val=0, max_val=100, step=1, value=50):
    """Create a parameter slider component."""
    return {"type": "slider", "min": min_val, "max": max_val, "step": step, "value": value}

def tip_card(title, content):
    """Create a tip card component."""
    return {"type": "card", "title": title, "content": content}

__all__ = ["param_slider", "tip_card"]
