#!/usr/bin/env python
"""
Launcher for Dash Mission Control with Streamlit warning suppression.

Run: python run_dash.py
    or: python -m run_dash
"""

import logging
import os
import sys
import warnings

# Suppress Streamlit warnings BEFORE any imports
warnings.filterwarnings("ignore", category=UserWarning, message=".*No runtime found.*")
warnings.filterwarnings("ignore", module="streamlit.*")

# Set logging levels for Streamlit to CRITICAL (suppress all output)
for logger_name in [
    "streamlit",
    "streamlit.runtime",
    "streamlit.runtime.caching",
    "streamlit.runtime.caching.cache_data_api",
]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Now run the main Dash app entry point
if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__) or ".")

    # Import after warning suppression is configured
    import app.dash_app  # This will run the app via if __name__ == "__main__"
