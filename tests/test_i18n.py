"""i18n helper tests."""

from __future__ import annotations

from app.utils.i18n import TRANSLATIONS, t


def test_translations_cover_nav_keys():
    for key in (
        "nav_home",
        "nav_studio",
        "nav_workflows",
        "welcome",
        "empty_title",
        "publish_title",
        "settings_title",
    ):
        assert key in TRANSLATIONS["en"]
        assert key in TRANSLATIONS["es"]


def test_fallback_to_english():
    assert t("welcome")  # uses session default via streamlit in app; test import path
    assert TRANSLATIONS["es"]["welcome"].startswith("Bienvenido")


def test_nav_studio_translation_values():
    assert TRANSLATIONS["en"]["nav_studio"] == "Data Studio"
    assert TRANSLATIONS["es"]["nav_studio"] == "Estudio de datos"


def test_all_nav_keys_present_in_both_locales():
    nav_keys = ["nav_home", "nav_studio", "nav_workflows", "nav_publish", "nav_settings"]
    for key in nav_keys:
        assert key in TRANSLATIONS["en"], f"Missing {key!r} in en"
        assert key in TRANSLATIONS["es"], f"Missing {key!r} in es"
        assert TRANSLATIONS["en"][key], f"Empty value for {key!r} in en"
        assert TRANSLATIONS["es"][key], f"Empty value for {key!r} in es"


def test_translation_keys_are_symmetric():
    en_keys = set(TRANSLATIONS["en"].keys())
    es_keys = set(TRANSLATIONS["es"].keys())
    assert en_keys == es_keys, f"Key mismatch — en only: {en_keys - es_keys}, es only: {es_keys - en_keys}"
