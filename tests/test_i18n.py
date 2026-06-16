"""i18n helper tests."""

from __future__ import annotations
import pytest


import sys
from unittest.mock import MagicMock, patch


def test_translations_cover_nav_keys():
    with patch.dict(sys.modules, {"streamlit": MagicMock()}):
        from app.utils.i18n import TRANSLATIONS

        for key in (
            "nav_home",
            "nav_workflows",
            "welcome",
            "empty_title",
            "publish_title",
            "settings_title",
        ):
            assert key in TRANSLATIONS["en"]
            assert key in TRANSLATIONS["es"]


def test_fallback_to_english():
    with patch.dict(sys.modules, {"streamlit": MagicMock()}):
        # Mock streamlit.session_state for this test
        import streamlit as st

        from app.utils.i18n import TRANSLATIONS, t

        st.session_state = {"lang": "en"}
        assert t("welcome")  # uses session default via streamlit in app; test import path
        assert TRANSLATIONS["es"]["welcome"].startswith("Bienvenido")
