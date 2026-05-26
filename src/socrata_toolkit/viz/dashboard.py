"""Streamlit Dashboard for DOT Sidewalk Toolkit.

A comprehensive, visually appealing project management dashboard that
ties together all toolkit modules into a single interface.

Pages:
1. Program Dashboard -- KPI cards with red/yellow/green, borough map
2. Task Board -- Kanban board with drag-and-drop-style columns
3. Construction Lists -- Build, prioritize, export
4. Contract Analytics -- Progress, budget, productivity charts
5. Data Explorer -- Fetch, profile, visualize Socrata datasets
6. Reports -- Generate and download reports
7. Settings -- Configure integrations and preferences

Run with::

    streamlit run socrata_toolkit/dashboard.py
"""

from __future__ import annotations

# This file is the Streamlit entry point. It uses lazy imports so the
# module can be imported without streamlit for testing/linting.


def main() -> None:
    """Launch the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(
        page_title="NYC DOT Sidewalk Toolkit",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for color-coded cards and styling
    st.markdown("""
    <style>
    .stMetric { border-radius: 8px; padding: 12px; }
    .status-green { background-color: #d4edda; border-left: 4px solid #28a745; padding: 10px; border-radius: 4px; margin: 4px 0; }
    .status-yellow { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; border-radius: 4px; margin: 4px 0; }
    .status-red { background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; border-radius: 4px; margin: 4px 0; }
    .task-card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 8px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .task-card-critical { border-left: 4px solid #dc3545; }
    .task-card-high { border-left: 4px solid #fd7e14; }
    .task-card-medium { border-left: 4px solid #ffc107; }
    .task-card-low { border-left: 4px solid #28a745; }
    .priority-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; color: white; }
    .kanban-col { background: #f8f9fa; border-radius: 8px; padding: 12px; min-height: 200px; }
    .metric-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    st.sidebar.title("NYC DOT Sidewalk Toolkit")
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Program Dashboard",
            "Task Board",
            "Construction Lists",
            "Contract Analytics",
            "Data Explorer",
            "Reports",
            "Settings",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("v0.3.0 | NYC DOT Sidewalk Inspection & Management")

    if page == "Program Dashboard":
        _page_dashboard(st)
    elif page == "Task Board":
        _page_task_board(st)
    elif page == "Construction Lists":
        _page_construction(st)
    elif page == "Contract Analytics":
        _page_contracts(st)
    elif page == "Data Explorer":
        _page_explorer(st)
    elif page == "Reports":
        _page_reports(st)
    elif page == "Settings":
        _page_settings(st)


# ---------------------------------------------------------------------------
# Page: Program Dashboard
# ---------------------------------------------------------------------------

def _page_dashboard(st) -> None:
    st.title("Program Dashboard")
    st.markdown("Real-time overview of sidewalk program KPIs and borough status.")

    uploaded = st.file_uploader("Upload program data (CSV/Excel)", type=["csv", "xlsx"], key="dash_upload")
    if uploaded:
        import pandas as pd
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.session_state["program_data"] = df

    if "program_data" not in st.session_state:
        st.info("Upload program data or use the Data Explorer to fetch from Socrata.")
        _show_demo_dashboard(st)
        return

    df = st.session_state["program_data"]
    from ..analysis.program import compute_program_dashboard
    try:
        dashboard = compute_program_dashboard(df)
    except Exception as e:
        st.error(f"Could not compute dashboard: {e}")
        return

    # KPI Cards
    cols = st.columns(len(dashboard.metrics))
    for col, metric in zip(cols, dashboard.metrics):
        color_class = f"status-{metric.status}"
        with col:
            st.markdown(f'<div class="{color_class}">', unsafe_allow_html=True)
            delta_str = f"{metric.delta_from_target:+.2f}" if metric.delta_from_target else ""
            st.metric(metric.name.replace("_", " ").title(), f"{metric.value:.2f}", delta_str)
            st.markdown("</div>", unsafe_allow_html=True)

    # Overall health badge
    health_colors = {"green": "#28a745", "yellow": "#ffc107", "red": "#dc3545"}
    st.markdown(f"""
    <div style="text-align:center; margin:20px 0;">
        <span style="background:{health_colors.get(dashboard.overall_health, '#6c757d')};
        color:white; padding:8px 24px; border-radius:20px; font-size:1.2em; font-weight:bold;">
        Program Health: {dashboard.overall_health.upper()}
        </span>
        <span style="margin-left:16px; font-size:1em;">
        {dashboard.green_count} green / {dashboard.yellow_count} yellow / {dashboard.red_count} red
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Borough breakdown if available
    if "borough" in df.columns:
        st.subheader("Borough Overview")
        from ..engineering.borough_analysis import borough_comparison_table
        table = borough_comparison_table(df)
        if not table.empty:
            st.dataframe(table, use_container_width=True)


def _show_demo_dashboard(st) -> None:
    """Show a demo dashboard with sample data."""
    st.subheader("Demo Dashboard")
    demo_cols = st.columns(5)
    demos = [
        ("Defect Density", "1.8", "green"),
        ("Throughput", "220 ft/day", "green"),
        ("Budget Variance", "+$12K", "yellow"),
        ("First Pass Yield", "88%", "yellow"),
        ("Rework Factor", "4.2%", "green"),
    ]
    for col, (name, value, status) in zip(demo_cols, demos):
        with col:
            st.markdown(f'<div class="status-{status}">', unsafe_allow_html=True)
            st.metric(name, value)
            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Task Board
# ---------------------------------------------------------------------------

def _page_task_board(st) -> None:
    st.title("Task Board")

    from ..tools.tasks import CATEGORY_COLORS, STATUS_LABELS, Task, TaskBoard

    # Load or create board
    if "board" not in st.session_state:
        st.session_state["board"] = TaskBoard("DOT Sidewalk Q1 2025")

    board = st.session_state["board"]

    # Board controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(board.name)
    with col2:
        if st.button("Save Board"):
            path = board.save("outputs/board.json")
            st.success(f"Saved to {path}")
    with col3:
        load_file = st.file_uploader("Load Board", type=["json"], key="board_load", label_visibility="collapsed")
        if load_file:
            import json as _json
            data = _json.loads(load_file.read())
            from pathlib import Path
            tmp = Path("outputs/_tmp_board.json")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(_json.dumps(data))
            st.session_state["board"] = TaskBoard.load(str(tmp))
            st.rerun()

    # Add task form
    with st.expander("Add New Task", expanded=False):
        with st.form("new_task"):
            t_title = st.text_input("Title")
            t_cols = st.columns(4)
            with t_cols[0]:
                t_assignee = st.text_input("Assignee")
            with t_cols[1]:
                t_priority = st.selectbox("Priority", ["critical", "high", "medium", "low"])
            with t_cols[2]:
                t_category = st.selectbox("Category", list(CATEGORY_COLORS.keys()))
            with t_cols[3]:
                t_due = st.date_input("Due Date")
            t_desc = st.text_area("Description", height=80)
            t_borough = st.selectbox("Borough", ["", "MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"])

            if st.form_submit_button("Create Task"):
                task = Task(
                    title=t_title, description=t_desc, assignee=t_assignee,
                    priority=t_priority, category=t_category,
                    due_date=str(t_due), borough=t_borough,
                )
                board.add_task(task)
                st.success(f"Created: {t_title}")
                st.rerun()

    # Board stats
    stats = board.stats()
    stat_cols = st.columns(6)
    stat_items = [
        ("Total", stats["total_tasks"]),
        ("Overdue", stats["overdue_count"]),
        ("Done %", f"{stats['completion_rate']}%"),
    ]
    for col, (label, val) in zip(stat_cols[:3], stat_items):
        col.metric(label, val)

    # Filters
    with st.expander("Filters"):
        f_cols = st.columns(4)
        with f_cols[0]:
            f_assignee = st.selectbox("Assignee", ["All"] + list(stats.get("by_assignee", {}).keys()))
        with f_cols[1]:
            f_priority = st.selectbox("Priority", ["All", "critical", "high", "medium", "low"])
        with f_cols[2]:
            f_category = st.selectbox("Category", ["All"] + list(stats.get("by_category", {}).keys()))
        with f_cols[3]:
            f_overdue = st.checkbox("Overdue only")

    # Kanban columns
    kanban_cols = st.columns(len(board.columns))
    for kcol, status in zip(kanban_cols, board.columns):
        with kcol:
            count = stats["by_status"].get(status, 0)
            st.markdown('<div class="kanban-col">', unsafe_allow_html=True)
            st.markdown(f"**{STATUS_LABELS.get(status, status)}** ({count})")
            st.markdown("---")

            tasks = board.filter_tasks(
                status=status,
                assignee=f_assignee if f_assignee != "All" else None,
                priority=f_priority if f_priority != "All" else None,
                category=f_category if f_category != "All" else None,
                overdue_only=f_overdue,
            )

            for tid, task in tasks:
                overdue_badge = " **OVERDUE**" if task.is_overdue else ""
                st.markdown(
                    f'<div class="task-card task-card-{task.priority}">'
                    f'<span class="priority-badge" style="background:{task.priority_color}">{task.priority.upper()}</span> '
                    f'<span style="background:{task.category_color};color:white;padding:1px 6px;border-radius:8px;font-size:0.75em;">{task.category}</span>'
                    f'{overdue_badge}<br/>'
                    f'<strong>{task.title}</strong><br/>'
                    f'<small>{task.assignee or "Unassigned"}'
                    f'{" | " + task.borough if task.borough else ""}'
                    f'{" | Due: " + task.due_date if task.due_date else ""}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Move buttons
                move_cols = st.columns(len(board.columns) - 1)
                other_statuses = [s for s in board.columns if s != status]
                for mcol, target in zip(move_cols, other_statuses):
                    if mcol.button(STATUS_LABELS.get(target, target)[:6], key=f"move_{tid}_{target}"):
                        board.move_task(tid, target)
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Construction Lists
# ---------------------------------------------------------------------------

def _page_construction(st) -> None:
    st.title("Construction List Manager")
    st.markdown("Build, prioritize, and export construction lists with conflict detection.")

    uploaded = st.file_uploader("Upload inspection data (CSV/Excel)", type=["csv", "xlsx"], key="cl_upload")
    if uploaded:
        import pandas as pd
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.session_state["cl_data"] = df
        st.success(f"Loaded {len(df)} records")

    if "cl_data" not in st.session_state:
        st.info("Upload inspection/work order data to get started.")
        return

    df = st.session_state["cl_data"]
    st.dataframe(df.head(20), use_container_width=True)

    from ..engineering.construction_list import (
        classify_scope,
        export_construction_list,
        flag_ada_locations,
        prioritize_construction_list,
        summarize_construction_list,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Prioritize & Classify"):
            df = prioritize_construction_list(df)
            df = classify_scope(df)
            df = flag_ada_locations(df)
            st.session_state["cl_data"] = df
            st.success("Construction list prioritized and classified")
            st.rerun()

    with col2:
        fmt = st.selectbox("Export Format", ["xlsx", "csv", "json", "geojson"])
        if st.button("Export"):
            path = f"outputs/construction_list.{fmt}"
            export_construction_list(df, path)
            st.success(f"Exported to {path}")

    if "_priority_score" in df.columns:
        summary = summarize_construction_list(df)
        st.subheader("Summary")
        scols = st.columns(4)
        scols[0].metric("Total Locations", summary.total_locations)
        scols[1].metric("ADA Required", summary.ada_count)
        scols[2].metric("High Priority", summary.high_priority_count)
        scols[3].metric("Avg Priority", f"{summary.avg_priority_score:.2f}")


# ---------------------------------------------------------------------------
# Page: Contract Analytics
# ---------------------------------------------------------------------------

def _page_contracts(st) -> None:
    st.title("Contract Analytics")
    st.markdown("Track progress, budget, and productivity across contracts.")

    uploaded = st.file_uploader("Upload contract data (CSV/Excel)", type=["csv", "xlsx"], key="ca_upload")
    if uploaded:
        import pandas as pd
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.session_state["ca_data"] = df

    if "ca_data" not in st.session_state:
        st.info("Upload contract data to begin analysis.")
        return

    df = st.session_state["ca_data"]
    from ..engineering.contract_analytics import (
        analyze_contract_progress,
        budget_analysis,
        productivity_metrics,
    )

    tab1, tab2, tab3 = st.tabs(["Progress", "Budget", "Productivity"])

    with tab1:
        try:
            progress = analyze_contract_progress(df)
            for p in progress:
                status_color = {"complete": "green", "in_progress": "yellow", "delayed": "red", "not_started": "gray"}.get(p.status, "gray")
                st.markdown(f'<div class="status-{status_color}">', unsafe_allow_html=True)
                st.markdown(f"**{p.contract_id}**: {p.pct_complete}% complete | {p.status.upper()} | {p.velocity_sqft_per_day} sqft/day")
                st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Could not analyze progress: {e}")

    with tab2:
        try:
            budget = budget_analysis(df)
            bcols = st.columns(4)
            bcols[0].metric("Planned", f"${budget.total_planned:,.0f}")
            bcols[1].metric("Actual", f"${budget.total_actual:,.0f}")
            bcols[2].metric("Variance", f"${budget.variance:,.0f}")
            bcols[3].metric("CPI", f"{budget.cost_performance_index:.2f}")
        except Exception as e:
            st.warning(f"Could not analyze budget: {e}")

    with tab3:
        try:
            prod = productivity_metrics(df)
            pcols = st.columns(4)
            pcols[0].metric("SqFt/Day", f"{prod.sqft_per_day:.1f}")
            pcols[1].metric("LF/Day", f"{prod.linear_feet_per_day:.1f}")
            pcols[2].metric("Cost/SqFt", f"${prod.cost_per_sqft:.2f}")
            pcols[3].metric("Efficiency", f"{prod.crew_efficiency:.2f}")
        except Exception as e:
            st.warning(f"Could not analyze productivity: {e}")


# ---------------------------------------------------------------------------
# Page: Data Explorer
# ---------------------------------------------------------------------------

def _page_explorer(st) -> None:
    st.title("Data Explorer")
    st.markdown("Fetch and explore datasets from NYC Open Data (Socrata).")

    col1, col2 = st.columns(2)
    with col1:
        domain = st.text_input("Domain", value="data.cityofnewyork.us")
    with col2:
        fourfour = st.text_input("Dataset ID (4x4)", value="h9gi-nx95")

    max_rows = st.slider("Max rows", 100, 50000, 5000)

    if st.button("Fetch Data"):
        from ..core.client import SocrataClient
        with st.spinner("Fetching..."):
            try:
                client = SocrataClient()
                df = client.fetch_dataframe(domain, fourfour, max_rows=max_rows)
                st.session_state["explorer_data"] = df
                st.success(f"Fetched {len(df)} rows")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    if "explorer_data" in st.session_state:
        df = st.session_state["explorer_data"]
        st.dataframe(df.head(100), use_container_width=True)

        tab1, tab2 = st.tabs(["Profile", "Quality"])
        with tab1:
            from ..analysis.core import profile_dataframe
            profile = profile_dataframe(df)
            st.json({"row_count": profile.row_count, "column_count": profile.column_count, "null_counts": profile.null_counts})
        with tab2:
            from ..governance.core import compute_quality_score
            score = compute_quality_score(df)
            qcols = st.columns(4)
            qcols[0].metric("Overall", f"{score.overall:.1f}")
            qcols[1].metric("Completeness", f"{score.completeness:.1f}%")
            qcols[2].metric("Validity", f"{score.validity:.1f}%")
            qcols[3].metric("Consistency", f"{score.consistency:.1f}%")


# ---------------------------------------------------------------------------
# Page: Reports
# ---------------------------------------------------------------------------

def _page_reports(st) -> None:
    st.title("Report Generator")

    report_type = st.selectbox("Report Type", [
        "Contract Status Report",
        "Program KPI Report",
        "Inquiry Response",
    ])

    if report_type == "Contract Status Report":
        uploaded = st.file_uploader("Upload contract data", type=["csv", "xlsx"], key="rpt_upload")
        if uploaded:
            import pandas as pd
            df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            from ..reports.reporting import generate_contract_report
            report = generate_contract_report(df)
            st.markdown(report.to_markdown())
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save as HTML"):
                    path = report.save("outputs/reports/contract_status.html")
                    st.success(f"Saved to {path}")
            with col2:
                if st.button("Save as Markdown"):
                    path = report.save("outputs/reports/contract_status.md")
                    st.success(f"Saved to {path}")

    elif report_type == "Program KPI Report":
        if "program_data" in st.session_state:
            from ..analysis.program import compute_program_dashboard
            from ..reports.reporting import generate_program_report
            dashboard = compute_program_dashboard(st.session_state["program_data"])
            report = generate_program_report(dashboard)
            st.markdown(report.to_markdown())
        else:
            st.info("Load program data on the Dashboard page first.")

    elif report_type == "Inquiry Response":
        inquiry_type = st.selectbox("Inquiry Type", ["contract_status", "location_status", "borough_overview"])
        param = st.text_input("Parameter (contract ID, location, or borough)")
        if st.button("Generate Response") and "explorer_data" in st.session_state:
            from ..reports.reporting import generate_inquiry_response
            kwargs = {}
            if inquiry_type == "contract_status":
                kwargs["contract_id"] = param
            elif inquiry_type == "location_status":
                kwargs["location"] = param
            elif inquiry_type == "borough_overview":
                kwargs["borough"] = param
            report = generate_inquiry_response(inquiry_type, st.session_state["explorer_data"], **kwargs)
            st.markdown(report.to_markdown())


# ---------------------------------------------------------------------------
# Page: Settings
# ---------------------------------------------------------------------------

def _page_settings(st) -> None:
    st.title("Settings")
    st.markdown("Configure toolkit integrations and preferences.")

    with st.expander("Socrata API", expanded=True):
        st.text_input("App Token", type="password", key="cfg_token")
        st.text_input("Default Domain", value="data.cityofnewyork.us", key="cfg_domain")

    with st.expander("Database Connections"):
        st.text_input("PostgreSQL DSN", type="password", key="cfg_pg")
        st.text_input("MongoDB URI", type="password", key="cfg_mongo")

    with st.expander("Export Preferences"):
        st.number_input("Default Max Rows", value=10000, key="cfg_max_rows")
        st.text_input("Reports Directory", value="outputs/reports", key="cfg_reports_dir")

    with st.expander("System Health"):
        if st.button("Run Doctor"):
            import importlib
            checks = {}
            for mod in ["requests", "click", "pandas", "openpyxl", "streamlit", "matplotlib", "shapely"]:
                try:
                    importlib.import_module(mod)
                    checks[mod] = "installed"
                except ImportError:
                    checks[mod] = "missing"
            for mod, status in checks.items():
                color = "green" if status == "installed" else "red"
                st.markdown(f'<span style="color:{color}">{"[OK]" if status == "installed" else "[MISSING]"}</span> {mod}', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
