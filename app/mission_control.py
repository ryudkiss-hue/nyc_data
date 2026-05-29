"""
Manhattan Mission Control — Unified Production Entry Point
==========================================================
NYC DOT Sidewalk Inspection & Management · Analyst Workspace · Apex Engine

Tabs
----
1. 🏠  Home            — status, datasets, onboarding
2. 🚀  Apex Engine     — Bayesian hiring analytics (MCMC + Prophet)
3. 🔍  Agency Workflows— QA/QC, spatial, contract, productivity
4. 📊  Data Quality    — profiling, SLA, anomaly detection
5. 🗺️  Spatial         — maps, hotspots, conflict detection
6. 🏛️  Governance      — lineage DAG, audit trail, compliance
7. 🤖  AI Copilot      — Gemini · OpenAI · Ollama (selectable)
8. ⚙️  Settings        — readiness, health, cache, logs

Entry points
------------
    streamlit run app/mission_control.py
    python main.py          # thin launcher shim
    Procfile / render.yaml  # cloud deploy
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

# ── App-level modules ───────────────────────────────────────────────────────
from app.data_loader import (
    DATASET_REGISTRY,
    load_dataset,
    token_status,
)
from app.ingest_log import log_event
from app.ui.theme import (
    inject_theme,
    render_agency_header,
    render_skip_link,
)
from app.utils.i18n import t

# ── View modules ────────────────────────────────────────────────────────────
from app.views.home import render_home_page
from app.views.settings import render_settings_page
from app.views.spatial_analytics import render_spatial_tab
from app.views.workflows import (
    render_roi_header,
    view_contract,
    view_productivity,
    view_qa,
    view_spatial,
)

log = logging.getLogger(__name__)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Manhattan Mission Control",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/ryudkiss-hue/nyc_data/wiki",
        "Report a bug": "https://github.com/ryudkiss-hue/nyc_data/issues",
        "About": "Manhattan Mission Control — NYC DOT Analytics Platform",
    },
)

# ── Constants ────────────────────────────────────────────────────────────────
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.5-flash:generateContent"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


# ── Session state bootstrap ─────────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict = {
        # Data
        "loaded_frames": {},
        "load_requested": False,
        # Apex Engine
        "apex_results": None,
        "df_jobs_cache": None,
        "df_payroll_cache": None,
        "apex_pipeline_ran_at": None,
        # Copilot
        "copilot_messages": [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your Manhattan Mission Control AI Copilot. "
                    "I'm hydrated with your live pipeline context. Ask me about "
                    "OMB hiring lag, Bayesian posteriors, PostGIS queries, "
                    "SLA compliance, data lineage, or any NYC open data question."
                ),
            }
        ],
        "llm_backend": "Gemini",
        # Governance
        "audit_trail": [],
        # UI
        "tour_seen": False,
        "onboarding_done": False,
        "lang": "en",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ── Data loading helpers ────────────────────────────────────────────────────
def _load_all_datasets(progress_slot: st.delta_generator.DeltaGenerator) -> dict[str, pd.DataFrame]:
    """Load every dataset in the registry, caching results in session state."""
    frames: dict[str, pd.DataFrame] = {}
    keys = list(DATASET_REGISTRY.keys())
    bar = st.progress(0, text="Loading datasets…")
    for i, key in enumerate(keys):
        bar.progress((i + 1) / len(keys), text=f"Loading {key}…")
        try:
            df = load_dataset(key)
            if df is not None and not df.empty:
                frames[key] = df
                log_event("load", dataset=key, rows=len(df))
                st.session_state["audit_trail"].append(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "action": "load",
                        "dataset": key,
                        "rows": len(df),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load %s: %s", key, exc)
    bar.empty()
    return frames


# ── AI Copilot helpers ──────────────────────────────────────────────────────
def _copilot_system_prompt(apex_results: dict | None, agency: str, title: str) -> str:
    if apex_results:
        lag = apex_results.get("best_lag", "?")
        yr = f"{apex_results.get('yield_rate', 0):.2f}"
        proj = int(apex_results.get("future_forecast", pd.DataFrame({"predicted_hires": [0]}))["predicted_hires"].sum())
    else:
        lag = yr = proj = "unknown"

    loaded = list(st.session_state.get("loaded_frames", {}).keys())
    datasets_ctx = ", ".join(loaded[:8]) or "none loaded"

    return f"""You are the Manhattan Mission Control AI — Senior Data Architect and Civil Operations Strategist for NYC open datasets.
Tone: precise, professional, command-center aesthetic.

Active pipeline context:
- Agency: "{agency}" | Title: "{title}"
- OMB Hiring Lag: {lag} months | Bayesian Yield: {yr}x | 12-Mo Projected Hires: {proj}
- Loaded datasets: {datasets_ctx}

You can help with: OMB lag analysis, MCMC posterior interpretation, PostGIS/DuckDB queries,
Prophet forecast anomalies, SLA compliance, data lineage, NYC Open Data exploration,
dbt source specs, Pandas ETL patterns.

Respond in Markdown, use bullet points, be concise and data-driven."""


def _query_gemini(prompt: str, sys_prompt: str, history: list) -> str:
    import requests  # local import to avoid cold-start cost

    if not GEMINI_API_KEY:
        return (
            "**[Offline]** Set `GEMINI_API_KEY` to enable Gemini responses.\n\n"
            f"*Question:* {prompt}"
        )
    contents = []
    for msg in history[1:]:
        contents.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}],
        })
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    try:
        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            json={"system_instruction": {"parts": [{"text": sys_prompt}]}, "contents": contents,
                  "generationConfig": {"temperature": 0.7}},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:  # noqa: BLE001
        return f"⚠️ Gemini error: {exc}"


def _query_openai(prompt: str, sys_prompt: str, history: list) -> str:
    try:
        import openai  # type: ignore[import]
    except ImportError:
        return "**[OpenAI unavailable]** Install `openai` package to use this backend."
    if not OPENAI_API_KEY:
        return "**[OpenAI offline]** Set `OPENAI_API_KEY` to enable OpenAI responses."
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    msgs = [{"role": "system", "content": sys_prompt}]
    for msg in history[1:]:
        msgs.append({"role": msg["role"], "content": msg["content"]})
    msgs.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=msgs, temperature=0.7)
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        return f"⚠️ OpenAI error: {exc}"


def _query_ollama(prompt: str, sys_prompt: str, history: list, model: str) -> str:
    import requests  # local import

    msgs = [{"role": "system", "content": sys_prompt}]
    for msg in history[1:]:
        msgs.append({"role": msg["role"], "content": msg["content"]})
    msgs.append({"role": "user", "content": prompt})
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": model, "messages": msgs, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        return (
            f"⚠️ Ollama error: {exc}\n\n"
            f"Make sure Ollama is running at `{OLLAMA_HOST}` with model `{model}` pulled."
        )


def _dispatch_llm(prompt: str, sys_prompt: str, history: list) -> str:
    backend = st.session_state.get("llm_backend", "Gemini")
    if backend == "Gemini":
        return _query_gemini(prompt, sys_prompt, history)
    if backend == "OpenAI":
        return _query_openai(prompt, sys_prompt, history)
    # Ollama
    model = st.session_state.get("ollama_model", "mistral")
    return _query_ollama(prompt, sys_prompt, history, model)


# ── Tab renderers ───────────────────────────────────────────────────────────

def _tab_home() -> None:
    render_home_page()


def _tab_apex(target_agency: str, target_title: str, scrape_start: int, scrape_end: int) -> None:
    try:
        from app.views.apex import render_apex_tab
        render_apex_tab(target_agency, target_title, scrape_start, scrape_end)
    except ImportError as exc:
        st.error(f"Apex Engine view not available: {exc}")


def _tab_workflows() -> None:
    frames = st.session_state.get("loaded_frames", {})
    if not frames:
        st.info(
            "Load datasets first — use the **Home** tab or the "
            "**Load All Datasets** button in the sidebar.",
            icon="📡",
        )
        return

    # Run all analytics workflows and cache results in session state
    if "workflow_results" not in st.session_state or st.button(
        "🔄 Refresh Workflows", key="refresh_workflows"
    ):
        with st.spinner("Running agency workflows…"):
            try:
                from app.analytics import run_all_workflows

                results = run_all_workflows(frames)
                st.session_state["workflow_results"] = results
            except Exception as exc:  # noqa: BLE001
                st.error(f"Workflow error: {exc}")
                return

    results = st.session_state.get("workflow_results", {})
    if not results:
        return

    render_roi_header(results.get("roi"))
    st.divider()
    sub = st.tabs(["🔍 QA / QC", "🗺️ Spatial", "📋 Contract", "🚶 Productivity"])
    with sub[0]:
        view_qa(results)
    with sub[1]:
        # view_spatial expects (results, map_layers_dict)
        map_layers = {k: v for k, v in frames.items()}
        view_spatial(results, map_layers)
    with sub[2]:
        view_contract(results)
    with sub[3]:
        view_productivity(results)


def _tab_quality() -> None:
    frames = st.session_state.get("loaded_frames", {})
    try:
        from app.views.quality_dashboard import render_quality_tab
        render_quality_tab(frames)
    except ImportError as exc:
        st.error(f"Quality dashboard view not available: {exc}")


def _tab_spatial() -> None:
    frames = st.session_state.get("loaded_frames", {})
    render_spatial_tab(frames)


def _tab_governance() -> None:
    frames = st.session_state.get("loaded_frames", {})
    try:
        from app.views.governance import render_governance_tab
        render_governance_tab(frames)
    except ImportError as exc:
        st.error(f"Governance view not available: {exc}")


def _tab_copilot(target_agency: str, target_title: str) -> None:
    apex_results = st.session_state.get("apex_results")
    sys_prompt = _copilot_system_prompt(apex_results, target_agency, target_title)

    # ── Backend status banner ───────────────────────────────────────────
    backend = st.session_state.get("llm_backend", "Gemini")
    if backend == "Gemini" and not GEMINI_API_KEY:
        st.warning("Gemini offline — set `GEMINI_API_KEY` in environment.", icon="⚠️")
    elif backend == "OpenAI" and not OPENAI_API_KEY:
        st.warning("OpenAI offline — set `OPENAI_API_KEY` in environment.", icon="⚠️")
    elif backend == "Ollama":
        model = st.session_state.get("ollama_model", "mistral")
        st.caption(f"🟢 Ollama — `{OLLAMA_HOST}` · model: `{model}`")

    st.caption(
        "Context-hydrated with active pipeline results: "
        f"agency, title, lag, yield, {len(st.session_state.get('loaded_frames', {}))} "
        "loaded datasets."
    )

    # ── Quick-action chips ──────────────────────────────────────────────
    chips = [
        ("OMB Latency", "Analyze the OMB hiring lag bottleneck in the active dataset."),
        ("MCMC Priors", "Explain the prior distributions and convergence in our Bayesian model."),
        ("PostGIS Join", "Write a PostGIS query joining city jobs locations with complaint coordinates."),
        ("SLA Compliance", "Summarize which datasets are out of SLA and what action is needed."),
        ("Forecast Anomalies", "Interpret the 12-month hire forecast and flag any anomalies."),
        ("DuckDB Query", "Write an optimized DuckDB SQL query for the sidewalk inspections dataset."),
    ]
    cols = st.columns(len(chips))
    for col, (label, query) in zip(cols, chips, strict=False):
        if col.button(label, key=f"chip_{label}", use_container_width=True):
            st.session_state.copilot_messages.append({"role": "user", "content": query})
            with st.spinner("Thinking…"):
                reply = _dispatch_llm(query, sys_prompt, st.session_state.copilot_messages)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})
            st.session_state.audit_trail.append(
                {"ts": datetime.now(timezone.utc).isoformat(), "action": "copilot_query",
                 "dataset": "—", "rows": 0}
            )
            st.rerun()

    st.divider()

    # ── Chat history ────────────────────────────────────────────────────
    for msg in st.session_state.copilot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask about pipeline, MCMC, SLA, PostGIS, DuckDB, forecasts…"):
        st.session_state.copilot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Contacting AI…"):
                reply = _dispatch_llm(user_input, sys_prompt, st.session_state.copilot_messages)
            st.markdown(reply)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})

    if st.button("🗑️ Clear Chat", key="clear_copilot"):
        st.session_state.copilot_messages = [
            {"role": "assistant", "content": "Chat cleared. Ready for new queries."}
        ]
        st.rerun()


def _tab_settings() -> None:
    render_settings_page()


# ── Sidebar ─────────────────────────────────────────────────────────────────

def _render_sidebar() -> tuple[str, str, int, int]:
    with st.sidebar:
        # Language
        lang = st.selectbox(
            t("language"), ["English", "Español"],
            index=0 if st.session_state.get("lang", "en") == "en" else 1,
            key="lang_select",
        )
        st.session_state["lang"] = "en" if lang == "English" else "es"

        st.markdown("---")

        # Dataset loading
        st.markdown("### 📡 Data")
        token = token_status()
        demo = token.get("demo_mode", False)
        auth = token.get("configured") or token.get("key_pair")

        if demo:
            st.caption("⚠️ Demo mode — synthetic data.")
        elif auth:
            st.caption("🔐 Socrata authenticated.")
        else:
            st.caption("🟡 Public tier — rate limits apply.")

        if st.button(
            "Load All Datasets",
            type="primary",
            use_container_width=True,
            key="load_all_btn",
            help="Pull all 16+ datasets from config/datasets.yaml via Socrata.",
        ):
            with st.spinner("Loading…"):
                slot = st.empty()
                frames = _load_all_datasets(slot)
                st.session_state["loaded_frames"] = frames
                st.session_state["load_requested"] = True
            st.success(f"Loaded {len(frames)} datasets.")
            st.rerun()

        loaded = st.session_state.get("loaded_frames", {})
        if loaded:
            st.caption(f"✅ {len(loaded)} datasets loaded")
            with st.expander("Dataset list", expanded=False):
                for k in loaded:
                    st.markdown(f"- `{k}` ({len(loaded[k]):,} rows)")

        st.markdown("---")

        # Apex Engine params
        st.markdown("### 🚀 Apex Engine")
        target_agency = st.text_input(
            "Agency",
            value=st.query_params.get("agency", "DEPARTMENT OF TRANSPORTATION"),
            key="apex_agency",
        )
        target_title = st.text_input(
            "Civil Service Title",
            value=st.query_params.get("title", "PROJECT ANALYST"),
            key="apex_title",
        )
        jid_range = st.slider(
            "JID Range", min_value=30000, max_value=50000,
            value=(35710, 35715), step=1,
        )
        scrape_start, scrape_end = jid_range
        jid_count = scrape_end - scrape_start + 1
        if jid_count > 20:
            st.warning(f"⏱️ {jid_count} JIDs ≈ {jid_count}–{jid_count * 2}s scrape time.")
        if jid_count > 100:
            st.error("Hard cap: reduce to ≤ 100 JIDs.")

        st.markdown("---")

        # AI Copilot backend
        st.markdown("### 🤖 AI Backend")
        backend = st.radio(
            "LLM",
            ["Gemini", "OpenAI", "Ollama"],
            index=["Gemini", "OpenAI", "Ollama"].index(
                st.session_state.get("llm_backend", "Gemini")
            ),
            key="llm_backend_radio",
            horizontal=True,
        )
        st.session_state["llm_backend"] = backend
        if backend == "Ollama":
            st.session_state["ollama_model"] = st.text_input(
                "Ollama model", value=st.session_state.get("ollama_model", "mistral")
            )

        st.markdown("---")

        # Reset / session
        if st.button("🔄 Reset Session", use_container_width=True, key="reset_btn"):
            for k in ["apex_results", "df_jobs_cache", "df_payroll_cache",
                      "apex_pipeline_ran_at", "loaded_frames"]:
                st.session_state[k] = None if k != "loaded_frames" else {}
            st.rerun()

        st.caption(f"v2.0 · {datetime.now().strftime('%Y-%m-%d')}")

    return target_agency, target_title, scrape_start, scrape_end


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    inject_theme()
    render_skip_link()

    # URL persistence
    qp = st.query_params
    if "agency" not in qp:
        pass  # will read defaults in sidebar

    token = token_status()
    render_agency_header(demo=token.get("demo_mode", False), live_auth=bool(token.get("configured")))

    target_agency, target_title, scrape_start, scrape_end = _render_sidebar()

    # Persist apex params to URL
    if st.session_state.get("apex_results") is not None:
        st.query_params["agency"] = target_agency
        st.query_params["title"] = target_title

    # ── Tabs ────────────────────────────────────────────────────────────
    (
        tab_home,
        tab_apex,
        tab_workflows,
        tab_quality,
        tab_spatial,
        tab_governance,
        tab_copilot,
        tab_settings,
    ) = st.tabs([
        "🏠 Home",
        "🚀 Apex Engine",
        "🔍 Agency Workflows",
        "📊 Data Quality",
        "🗺️ Spatial",
        "🏛️ Governance",
        "🤖 AI Copilot",
        "⚙️ Settings",
    ])

    with tab_home:
        _tab_home()

    with tab_apex:
        _tab_apex(target_agency, target_title, scrape_start, scrape_end)

    with tab_workflows:
        _tab_workflows()

    with tab_quality:
        _tab_quality()

    with tab_spatial:
        _tab_spatial()

    with tab_governance:
        _tab_governance()

    with tab_copilot:
        _tab_copilot(target_agency, target_title)

    with tab_settings:
        _tab_settings()


if __name__ == "__main__":
    main()
