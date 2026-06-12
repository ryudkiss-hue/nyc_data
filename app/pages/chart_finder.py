"""Chart Finder — Interactive visualization recommender (Streamlit page)."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from socrata_toolkit.viz.chart_finder import ChartFinder

st.set_page_config(
    page_title="Chart Finder",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Chart Finder")
st.markdown(
    """
Intelligent visualization recommender. Upload your data and get smart chart suggestions
based on your DataFrame's structure, column types, and cardinality.

**Features:**
- Auto-analyze column types (numeric, categorical, datetime, spatial)
- Score 25+ visualization types by suitability
- Get code snippets to visualize immediately
- Filter by research question or analysis type
"""
)

# ============================================================================
# SIDEBAR: Data Upload & Controls
# ============================================================================

st.sidebar.header("📥 Upload Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV, Excel, or JSON",
    type=["csv", "xlsx", "xls", "json"],
    help="Upload your data for chart recommendations",
)

# Demo mode
if st.sidebar.checkbox("🎯 Use Demo Data"):
    import numpy as np

    np.random.seed(42)
    demo_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=100),
        "borough": np.random.choice(["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"], 100),
        "violation_count": np.random.poisson(5, 100),
        "repair_cost": np.random.exponential(3000, 100),
        "condition_score": np.random.normal(65, 15, 100),
        "material_type": np.random.choice(["Concrete", "Brick", "Asphalt"], 100),
        "status": np.random.choice(["Open", "Complete", "Pending", "Dismissed"], 100),
    })
    uploaded_file = None  # Clear any actual upload

if uploaded_file is not None:
    # Load uploaded file
    try:
        if uploaded_file.name.endswith(".json"):
            df = pd.read_json(uploaded_file)
        elif uploaded_file.name.endswith(("xlsx", "xls")):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)
        use_demo = False
    except Exception as e:
        st.error(f"Error loading file: {e}")
        df = None
elif st.sidebar.checkbox("🎯 Use Demo Data"):
    use_demo = True
else:
    df = None

# ============================================================================
# MAIN: Analysis & Recommendations
# ============================================================================

if df is not None and not df.empty:
    # Initialize ChartFinder
    finder = ChartFinder(df)

    # ========================================================================
    # TAB 1: Data Profile
    # ========================================================================

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Profile", "🎯 Recommendations", "🔍 All Charts", "💡 Hypothesis"])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rows", f"{finder.profile.row_count:,}")
        col2.metric("Columns", finder.profile.col_count)
        col3.metric("Numeric", len(finder.profile.numeric_cols))
        col4.metric("Categorical", len(finder.profile.categorical_cols))

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Column Types")
            col_types = pd.DataFrame({
                "Type": ["Numeric", "Categorical", "Datetime", "Spatial"],
                "Count": [
                    len(finder.profile.numeric_cols),
                    len(finder.profile.categorical_cols),
                    len(finder.profile.datetime_cols),
                    len(finder.profile.geometry_cols),
                ],
            })
            st.dataframe(col_types, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Detected Patterns")
            if finder.profile.analysis_patterns:
                for pattern in finder.profile.analysis_patterns:
                    st.info(f"✓ {pattern.title()}", icon="ℹ️")
            else:
                st.warning("No patterns detected. Try adding more diverse columns.")

        # Column details
        st.subheader("Column Cardinality & Completeness")
        card_df = pd.DataFrame({
            "Column": list(finder.profile.cardinalities.keys()),
            "Distinct": list(finder.profile.cardinalities.values()),
            "Null %": [finder.profile.null_fractions.get(c, 0) * 100 for c in finder.profile.cardinalities.keys()],
        })
        card_df = card_df.sort_values("Distinct", ascending=False)
        st.dataframe(card_df, use_container_width=True, hide_index=True)

    # ========================================================================
    # TAB 2: Chart Recommendations
    # ========================================================================

    with tab2:
        col_n, col_filter = st.columns([1, 3])
        with col_n:
            top_n = st.slider("Top-N recommendations", 1, 15, 5)

        # Get recommendations
        recs = finder.recommend(top_n=top_n)

        if recs:
            for rec in recs:
                with st.expander(f"{rec.rank}. **{rec.chart_name}** (Score: {rec.score:.2f})", expanded=(rec.rank == 1)):
                    col_left, col_right = st.columns([1, 2])

                    with col_left:
                        st.markdown("**Details**")
                        st.write(f"🔧 Function: `{rec.function_name}`")
                        st.write(f"📦 Module: `{rec.module}`")
                        st.write(f"📊 Type: {rec.analysis_type}")
                        st.write(f"💡 {rec.reason}")

                    with col_right:
                        st.markdown("**Column Requirements**")
                        if rec.required_cols:
                            st.write(f"🔴 Required: {', '.join(rec.required_cols)}")
                        if rec.suggested_cols:
                            st.write(f"🟢 Optional: {', '.join(rec.suggested_cols)}")
                        if rec.example_code:
                            st.code(rec.example_code, language="python")

    # ========================================================================
    # TAB 3: All Available Charts
    # ========================================================================

    with tab3:
        st.markdown(
            """
        Reference for all 25+ available charts. Use these to understand what each visualization
        offers and when to use it.
        """
        )
        all_charts = finder._get_all_charts()

        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Search charts...", placeholder="e.g., 'trend', 'comparison'")
        with col2:
            analysis_filter = st.multiselect(
                "Filter by analysis type",
                ["temporal", "comparative", "distributional", "multivariate", "spatial", "relational"],
            )

        # Filter charts
        filtered = all_charts
        if search_term:
            filtered = [
                c
                for c in filtered
                if search_term.lower() in c["name"].lower()
                or search_term.lower() in c["reason"].lower()
            ]
        if analysis_filter:
            filtered = [
                c for c in filtered if any(p in c.get("analysis_patterns", []) for p in analysis_filter)
            ]

        # Display as cards
        for chart in filtered:
            with st.container(border=True):
                st.markdown(f"### {chart['name']}")
                col_l, col_r = st.columns([1, 3])
                with col_l:
                    st.code(f"{chart['function']}()", language="python")
                with col_r:
                    st.write(f"**{chart['reason']}**")
                    st.caption(f"🎯 {chart['hypothesis_fit']}")

    # ========================================================================
    # TAB 4: Hypothesis-Driven Recommendations
    # ========================================================================

    with tab4:
        st.markdown(
            """
        Have a specific research question? Enter it below and get chart recommendations
        tailored to your hypothesis.
        """
        )

        hypothesis = st.text_area(
            "What are you trying to find out?",
            placeholder="Examples:\n- Compare violation rates across boroughs\n- Track trends over time\n- Identify spatial hotspots\n- Correlate cost with defect type",
            height=100,
        )

        if st.button("🔍 Find Charts for This Question", use_container_width=True, type="primary"):
            if hypothesis.strip():
                recs = finder.recommend_for_hypothesis(hypothesis)
                st.success(f"Found {len(recs)} recommendations!")

                for rec in recs:
                    with st.expander(f"{rec.rank}. **{rec.chart_name}** (Fit: {rec.score:.2f})", expanded=(rec.rank == 1)):
                        st.write(f"**Why this works:** {rec.reason}")
                        st.write(f"**For this question:** {rec.hypothesis_fit}")
                        if rec.example_code:
                            st.code(rec.example_code, language="python")
            else:
                st.warning("Please enter a research question.")

    # ========================================================================
    # FOOTER
    # ========================================================================

    st.divider()
    st.markdown(
        """
    **Next Steps:**
    1. Pick a chart from the recommendations
    2. Copy the example code
    3. Run it in your notebook or script
    4. Customize as needed (colors, labels, filters, etc.)

    **Need help?** Check the [Chart Registry](docs/CHART_REGISTRY.md) for detailed documentation
    on all 65+ visualizations.
    """
    )

else:
    st.info("👈 Upload data or enable demo mode in the sidebar to get started!")

    # Show demo charts
    with st.expander("🎯 See Example Recommendations"):
        st.markdown(
            """
        **Example:** Inspection violations dataset

        | Rank | Chart | Score | Why |
        |------|-------|-------|-----|
        | 1 | Parallel Coordinates | 8.5 | 4 numeric cols + borough grouping |
        | 2 | Trend Line | 7.8 | Has temporal data (date) |
        | 3 | Borough Bar Chart | 7.2 | Borough + violation_count perfect fit |
        | 4 | Clustermap | 6.9 | Multi-metric comparison by geography |
        | 5 | Ridge Plot | 6.5 | Distribution differences by borough |
        """
        )
