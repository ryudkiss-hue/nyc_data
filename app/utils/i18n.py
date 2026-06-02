"""Lightweight i18n for Mission Control (EN / ES)."""

from __future__ import annotations

import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Welcome to Manhattan Mission Control",
        "welcome_sub": "NYC DOT Sidewalk Inspection & Management (SIM)",
        "upload_prompt": "Load sample data or connect Socrata to begin.",
        "analyze": "Open Analyst Workflows",
        "load_sample": "Load sample data (demo mode)",
        "upload_csv": "Upload your own CSV",
        "new_here": "New here? Complete onboarding on Home, then open the Agency runbook in docs/AGENCY_RUNBOOK.md.",
        "language": "Language / Idioma",
        "nav_home": "Home",
        "nav_workflows": "Analyst Workflows",
        "nav_publish": "Publish & Pack",
        "nav_settings": "Settings & Quality",
        "navigation": "Navigation",
        "workflows": "Workflows",
        "data_load": "Data load",
        "refresh_cache": "Refresh cache",
        "demo_active": "Demo mode — no live API calls.",
        "clear_session": "Clear session",
        "onboarding_title": "First-time setup",
        "onboarding_done": "Mark onboarding complete",
        "onboarding_complete_msg": "Onboarding complete. Use the sidebar to open analyst workflows.",
        "tour_title": "Guided tour",
        "tour_step1": "1. Home — check auth status and latest analyst pack.",
        "tour_step2": "2. Analyst Workflows — QA, spatial, contract, and productivity views.",
        "tour_step3": "3. Publish & Pack — run weekly pack and dry-run publish.",
        "tour_step4": "4. Settings — readiness score, completeness checklist, ingest log.",
        "empty_title": "No workflow data loaded yet",
        "empty_body": "Load demo data or configure SOCRATA_APP_TOKEN in .env for live Socrata pulls.",
        "run_demo": "Load demo data now",
        "go_workflows": "Go to Analyst Workflows",
        "metric_datasets": "Socrata datasets",
        "metric_auth": "Auth",
        "metric_pack": "Latest pack",
        "auth_configured": "Configured",
        "auth_demo": "Demo / public",
        "publish_title": "Publish & Analyst Pack",
        "publish_caption": "Run the weekly pack, then publish to share paths, email, or BI (dry-run first).",
        "run_pack": "Run Analyst Pack",
        "publish_pack_btn": "Publish pack",
        "dry_run": "Dry run (recommended)",
        "offline_pack": "Offline pack run",
        "settings_title": "Settings & Quality",
        "tab_readiness": "Readiness",
        "tab_completeness": "Completeness",
        "tab_health": "System health",
        "tab_logs": "Ingestion log",
    },
    "es": {
        "welcome": "Bienvenido a Manhattan Mission Control",
        "welcome_sub": "Inspección y gestión de aceras NYC DOT (SIM)",
        "upload_prompt": "Cargue datos de muestra o conecte Socrata para comenzar.",
        "analyze": "Abrir flujos de analista",
        "load_sample": "Cargar datos de muestra (modo demo)",
        "upload_csv": "Subir su propio CSV",
        "new_here": "¿Nuevo? Complete la configuración en Inicio y consulte docs/AGENCY_RUNBOOK.md.",
        "language": "Language / Idioma",
        "nav_home": "Inicio",
        "nav_workflows": "Flujos de analista",
        "nav_publish": "Publicar y paquete",
        "nav_settings": "Configuración y calidad",
        "navigation": "Navegación",
        "workflows": "Flujos",
        "data_load": "Carga de datos",
        "refresh_cache": "Actualizar caché",
        "demo_active": "Modo demo — sin llamadas API en vivo.",
        "clear_session": "Borrar sesión",
        "onboarding_title": "Configuración inicial",
        "onboarding_done": "Marcar configuración completa",
        "onboarding_complete_msg": "Configuración completa. Use la barra lateral para abrir flujos.",
        "tour_title": "Recorrido guiado",
        "tour_step1": "1. Inicio — estado de autenticación y último paquete.",
        "tour_step2": "2. Flujos — QA, espacial, contratos y productividad.",
        "tour_step3": "3. Publicar — ejecutar paquete y simulación de publicación.",
        "tour_step4": "4. Configuración — preparación, lista de verificación y registro.",
        "empty_title": "Aún no hay datos cargados",
        "empty_body": "Cargue datos demo o configure SOCRATA_APP_TOKEN en .env.",
        "run_demo": "Cargar datos demo",
        "go_workflows": "Ir a flujos de analista",
        "metric_datasets": "Conjuntos Socrata",
        "metric_auth": "Autenticación",
        "metric_pack": "Último paquete",
        "auth_configured": "Configurado",
        "auth_demo": "Demo / público",
        "publish_title": "Publicar y paquete de analista",
        "publish_caption": "Ejecute el paquete semanal y publique (simulación primero).",
        "run_pack": "Ejecutar paquete",
        "publish_pack_btn": "Publicar paquete",
        "dry_run": "Simulación (recomendado)",
        "offline_pack": "Paquete sin conexión",
        "settings_title": "Configuración y calidad",
        "tab_readiness": "Preparación",
        "tab_completeness": "Lista de verificación",
        "tab_health": "Salud del sistema",
        "tab_logs": "Registro de ingesta",
    },
}

LANG_LABELS = {"en": "English", "es": "Español"}
LABEL_TO_CODE = {v: k for k, v in LANG_LABELS.items()}


def set_language(lang_code: str) -> None:
    st.session_state["lang"] = lang_code if lang_code in TRANSLATIONS else "en"


def current_language() -> str:
    return st.session_state.get("lang", "en")


def t(key: str) -> str:
    lang = current_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def render_language_selector() -> None:
    label = st.sidebar.selectbox(
        t("language"),
        list(LANG_LABELS.values()),
        index=0 if current_language() == "en" else 1,
        key="lang_selector",
    )
    set_language(LABEL_TO_CODE.get(label, "en"))
