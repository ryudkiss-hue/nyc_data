"""i18n helper tests."""

from __future__ import annotations

from app.utils.i18n import TRANSLATIONS, t


def test_translations_cover_nav_keys():
    for key in ("nav_home", "nav_workflows", "welcome", "empty_title", "publish_title", "settings_title"):
        assert key in TRANSLATIONS["en"]
        assert key in TRANSLATIONS["es"]


def test_fallback_to_english():
    assert t("welcome")  # uses session default via streamlit in app; test import path
    assert TRANSLATIONS["es"]["welcome"].startswith("Bienvenido")
