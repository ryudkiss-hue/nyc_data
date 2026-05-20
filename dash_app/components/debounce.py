"""Debounce pattern for slider-heavy callbacks (300ms default)."""



from __future__ import annotations



from dash import dcc, html





def debounce_bundle(prefix: str, *, interval_ms: int = 300) -> list:

    """Return Store + Interval used to debounce slider inputs.



    Wire sliders -> ``{prefix}-pending`` Store; preview callback listens to

    ``{prefix}-debounced`` Store; tick callback copies pending -> debounced.

    """

    return [

        dcc.Store(id=f"{prefix}-pending"),

        dcc.Store(id=f"{prefix}-debounced"),

        dcc.Interval(

            id=f"{prefix}-debounce-tick",

            interval=interval_ms,

            n_intervals=0,

            disabled=True,

        ),

    ]


