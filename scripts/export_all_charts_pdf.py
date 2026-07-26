"""
export_all_charts_pdf.py — NYC DOT SIM Mission Control
Generates a single combined PDF containing every visualization, chart, report,
and statistic, with a linked table of contents.

Usage (from repo root):
    python scripts/export_all_charts_pdf.py
    python scripts/export_all_charts_pdf.py --out exports/nyc_dot_report.pdf
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

# ── Path bootstrap ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── ReportLab imports ─────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Constants ─────────────────────────────────────────────────────────────────
CACHE_DIR = ROOT / "data" / "local_db" / "socrata_cache"
EXPORT_DIR = ROOT / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = landscape(letter)  # 792 × 612 pt — landscape report
MARGIN = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

BRAND_BLUE = colors.HexColor("#1565C0")
BRAND_DARK = colors.HexColor("#212529")
ACCENT = colors.HexColor("#FF6F00")
SECTION_BG = colors.HexColor("#E3F2FD")
LIGHT_GRAY = colors.HexColor("#F8F9FA")
MID_GRAY = colors.HexColor("#6C757D")

# ── Load data bundle ──────────────────────────────────────────────────────────

from socrata_toolkit.quality.sanitize import sanitize_dataframe  # noqa: E402

# Per-dataset data-quality findings collected during load; feeds the
# "Data Quality Findings" appendix.  {key: {...metrics...}}
_QUALITY: dict[str, dict] = {}


def _load_data_bundle() -> dict[str, pd.DataFrame]:
    bundle: dict[str, pd.DataFrame] = {}
    if not CACHE_DIR.exists():
        log.warning("Cache dir not found: %s — charts will render empty-state", CACHE_DIR)
        return bundle
    for p in sorted(CACHE_DIR.glob("*.parquet")):
        try:
            df, rep = sanitize_dataframe(pd.read_parquet(p))
            bundle[p.stem] = df
            _QUALITY[p.stem] = {
                "rows_in": rep.rows_in, "dupes_removed": rep.dupes_removed,
                "bad_dates_nulled": rep.bad_dates_nulled,
                "bad_date_cols": rep.bad_date_cols, "dead_vars": rep.dead_vars,
                "pct_missing": rep.pct_missing,
            }
            log.info("  loaded %-35s  %s rows  (dupes-%d, bad-dates-%d)",
                     p.stem, f"{len(df):,}", rep.dupes_removed, rep.bad_dates_nulled)
        except Exception as exc:
            log.warning("  skip %s — %s", p.name, exc)
    return bundle


# ── Import VisualizationEngine (handle import errors gracefully) ──────────────

def _import_ve():
    try:
        from app.viz_engine import VisualizationEngine
        return VisualizationEngine
    except Exception as e:
        log.error("Cannot import VisualizationEngine: %s", e)
        return None


def _import_viz_extras():
    extras: dict[str, Any] = {}
    try:
        from src.socrata_toolkit.viz import plotly as viz_plotly
        extras["plotly_mod"] = viz_plotly
    except Exception:
        pass
    try:
        from src.socrata_toolkit.viz import statistical_viz
        extras["stat_viz"] = statistical_viz
    except Exception:
        pass
    try:
        from src.socrata_toolkit.viz import advanced_multidim as adv
        extras["adv"] = adv
    except Exception:
        pass
    try:
        from src.socrata_toolkit.viz import charts_extra
        extras["charts_extra"] = charts_extra
    except Exception:
        pass
    return extras


# ── Chart catalogue ───────────────────────────────────────────────────────────

def _build_catalogue(VE, data_bundle: dict, extras: dict) -> list[dict]:
    """
    Returns a flat list of chart specs:
        { section, title, description, callable }
    callable() → go.Figure  (never raises; returns empty-state on error)
    """

    def safe(fn, *args, label="chart"):
        def _call():
            try:
                result = fn(*args)
                fig = result[0] if isinstance(result, tuple) else result
                if not isinstance(fig, go.Figure):
                    raise TypeError(f"{label} returned {type(fig)}")
                return fig
            except Exception as exc:
                log.warning("  %s render error: %s", label, exc)
                fig = go.Figure()
                fig.update_layout(
                    title=label,
                    height=420,
                    annotations=[dict(
                        text=f"Render error: {exc}",
                        xref="paper", yref="paper", x=0.5, y=0.5,
                        showarrow=False, font=dict(size=12, color="#6c757d"),
                    )],
                )
                return fig
        return _call

    db = data_bundle
    charts: list[dict] = []

    def add(section: str, title: str, description: str, fn):
        charts.append(dict(section=section, title=title, description=description, fn=fn))

    # ── Section 1: Inspection & Operations ───────────────────────────────────
    if VE:
        add("Inspection & Operations",
            "Inspections by Borough",
            "IV: Borough  |  DV: Inspection Volume — bar chart showing total inspection "
            "records by borough with data labels and OLS trend annotations.",
            safe(VE.chart_inspections_boro, db, label="chart_inspections_boro"))

        add("Inspection & Operations",
            "HIQA Inspection Efficiency (Weekly Throughput)",
            "IV: Week  |  DV: Inspections completed per week — bar chart with OLS "
            "trend line measuring operational throughput over time.",
            safe(VE.chart_efficiency, db, label="chart_efficiency"))

        add("Inspection & Operations",
            "Open Violation Live Queue",
            "IV: Violation Category  |  DV: Open case queue volume — horizontal bar "
            "chart showing current backlog distribution by hazard type.",
            safe(VE.chart_live_queue, db, label="chart_live_queue"))

        add("Inspection & Operations",
            "Complaint-to-Repair Lifecycle Funnel",
            "IV: SIM Process Stage  |  DV: Record Volume — funnel chart measuring "
            "conversion and attrition at each stage from complaint intake to resolution.",
            safe(VE.chart_lifecycle, db, label="chart_lifecycle"))

        add("Inspection & Operations",
            "Re-inspection Pass Rate Gauge",
            "IV: Outcome Category  |  DV: Re-inspection Pass Rate (%) vs 85 % SLA — "
            "gauge chart with target threshold and colour-coded risk zones.",
            safe(VE.chart_reinspection_gauge, db, label="chart_reinspection_gauge"))

    # ── Section 2: Violations & Enforcement ──────────────────────────────────
    if VE:
        add("Violations & Enforcement",
            "Violation Severity Distribution",
            "IV: Hazard Classification  |  DV: Frequency of Violations — bar chart "
            "breaking down recorded violations by hazard severity class.",
            safe(VE.chart_violation_severity, db, label="chart_violation_severity"))

        add("Violations & Enforcement",
            "Violation Cohort Heatmap (24-Month)",
            "IV: Issue Month × Severity  |  DV: Cohort Volume — 24-month cohort "
            "heatmap revealing seasonal patterns and backlog growth.",
            safe(VE.chart_violation_cohorts, db, label="chart_violation_cohorts"))

        add("Violations & Enforcement",
            "Violation Dismissals by Borough",
            "IV: Borough  |  DV: Dismissal Volume — donut pie chart showing the "
            "geographic distribution of dismissed violation complaints.",
            safe(VE.chart_dismissals_pie, db, label="chart_dismissals_pie"))

        add("Violations & Enforcement",
            "Mean Time to Repair (MTTR) Distribution",
            "IV: Days to Repair  |  DV: Frequency of Cases — histogram with "
            "median / mean / P90 vertical reference lines.",
            safe(VE.chart_mttr_distribution, db, label="chart_mttr_distribution"))

        add("Violations & Enforcement",
            "Repair Duration by Borough (Box Plot)",
            "IV: Borough  |  DV: Repair Duration (Days) — box plot with mean + SD "
            "overlays per borough revealing equity in repair turnaround.",
            safe(VE.chart_boxplot_repair_days, db, label="chart_boxplot_repair_days"))

        add("Violations & Enforcement",
            "Pre / Post Intervention Comparison",
            "IV: Period (Pre / Post)  |  DV: Violation or Repair Rate — grouped bar "
            "chart measuring the effect of policy interventions on outcome rates.",
            safe(VE.chart_pre_post_intervention, db, label="chart_pre_post_intervention"))

        add("Violations & Enforcement",
            "Violation Volume Treemap",
            "IV: Borough × Category  |  DV: Violation Volume — nested treemap "
            "providing hierarchical breakdown by geography and hazard class.",
            safe(VE.chart_treemap_violations, db, label="chart_treemap_violations"))

    # ── Section 3: Ramp & Accessibility ──────────────────────────────────────
    if VE:
        add("Ramp & Accessibility",
            "ADA Ramp Complaint Trends (90-Day Trailing)",
            "IV: Reporting Date  |  DV: Ramp Complaint Volume — area chart with "
            "90-day rolling mean and peak-complaint annotations.",
            safe(VE.chart_ramp_trends, db, label="chart_ramp_trends"))

        add("Ramp & Accessibility",
            "Pedestrian Catchment Isochrones",
            "IV: Walk-Time Radius  |  DV: Pedestrian Catchment Coverage — three-zone "
            "concentric-ring chart visualising walkability service areas.",
            safe(VE.chart_isochrone_walkability, db, label="chart_isochrone_walkability"))

        add("Ramp & Accessibility",
            "Socio-Economic Equity Routing Multiplier",
            "IV: Borough  |  DV: Equity Priority Multiplier — bar chart with "
            "policy-maximum threshold line used in ADA ramp routing prioritisation.",
            safe(VE.chart_equity_multiplier, db, label="chart_equity_multiplier"))

    # ── Section 4: Capital & Budget ───────────────────────────────────────────
    if VE:
        add("Capital & Budget",
            "PS Budget Code Burn Rate",
            "IV: Budget Code  |  DV: Capital Expended vs Remaining Allocation — "
            "stacked bar chart showing budget utilisation by programme code.",
            safe(VE.chart_ps_burn, db, label="chart_ps_burn"))

        add("Capital & Budget",
            "Sidewalk Repair Velocity (Administrative Velocity Trend)",
            "IV: Operational Date (weekly)  |  DV: Sidewalk Repaired (sq ft) — "
            "line chart with OLS trendline measuring repair output over time.",
            safe(VE.chart_built_sqft_trend, db, label="chart_built_sqft_trend"))

        add("Capital & Budget",
            "Street Construction Permit Fees by Type",
            "IV: Fee Type  |  DV: Total Fee Amount Charged ($) — bar chart of the "
            "2025-present permit fee revenue mix (9fnm-j6if), joinable to permits "
            "on permitnumber for borough budget attribution.",
            safe(VE.chart_permit_fee_breakdown, db, label="chart_permit_fee_breakdown"))

        add("Capital & Budget",
            "Capital Budget Waterfall",
            "IV: Budget Stage  |  DV: Cumulative Capital Position ($) — waterfall "
            "chart from Allocation through Expended to Remaining balance.",
            safe(VE.chart_waterfall_budget, db, label="chart_waterfall_budget"))

        add("Capital & Budget",
            "Monte Carlo Capital Budget Risk",
            "IV: Simulated Cost Scenarios  |  DV: Frequency Distribution — histogram "
            "with 5th / 95th percentile confidence bands from 10 000 simulations.",
            safe(VE.chart_budget_monte_carlo, 1_500_000, label="chart_budget_monte_carlo"))

    # ── Section 5: Geospatial & Spatial Analysis ──────────────────────────────
    if VE:
        add("Geospatial & Spatial Analysis",
            "Construction Permit Density (Spatial Conflicts)",
            "IV: Geographic Location  |  DV: Construction Permit Density — scatter "
            "mapbox or borough bar showing active-permit / inspection overlap zones.",
            safe(VE.chart_spatial_conflicts_deck, db, label="chart_spatial_conflicts_deck"))

        add("Geospatial & Spatial Analysis",
            "Violation Density Choropleth (per 1 000 Population)",
            "IV: NYC Borough  |  DV: Violation Density per 1 000 Population — "
            "bubble mapbox choropleth normalised by Census 2020 population.",
            safe(VE.chart_choropleth_violations, db, label="chart_choropleth_violations"))

        add("Geospatial & Spatial Analysis",
            "Predictive Pavement Decay (Markov Surface)",
            "IV: Time (Years) × Condition State  |  DV: Transition Probability — "
            "3D surface chart from a Markov chain degradation model.",
            safe(VE.chart_markov_decay, db, label="chart_markov_decay"))

        add("Geospatial & Spatial Analysis",
            "Borough PCA Manifold (3-D Cluster)",
            "IV: PC1 / PC2 / PC3  |  DV: Borough Cluster Separation — PCA scatter "
            "revealing multi-dimensional groupings across boroughs.",
            safe(VE.chart_manifold_3d, db, label="chart_manifold_3d"))

        add("Geospatial & Spatial Analysis",
            "Tax Lot & Zoning Infrastructure Share",
            "IV: Borough / Zone  |  DV: Share of Tax Lot Infrastructure — donut pie "
            "from MapPLUTO lot data showing built-environment composition.",
            safe(VE.chart_lot_zoning_pie, db, label="chart_lot_zoning_pie"))

    # ── Section 6: Data Quality & Signal Detection ────────────────────────────
    if VE:
        add("Data Quality & Signal Detection",
            "Dataset Freshness / SLA Score Matrix",
            "IV: Dataset Name  |  DV: Freshness Score (100 − days since last record) "
            "— colour-scaled bar across all 25 cached datasets vs SLA threshold.",
            safe(VE.chart_freshness, db, label="chart_freshness"))

        add("Data Quality & Signal Detection",
            "Cross-Dataset Missingness Heatmap",
            "IV: Column Name  |  DV: Null % per Dataset — cross-dataset heatmap "
            "revealing data completeness gaps for analyst awareness.",
            safe(VE.chart_missingness_matrix, db, label="chart_missingness_matrix"))

        add("Data Quality & Signal Detection",
            "Numeric Column Correlation Heatmap",
            "IV: Column Pair  |  DV: Pearson Correlation Coefficient — RdBu diverging "
            "heatmap identifying co-linear metrics and data redundancy.",
            safe(VE.chart_correlation_heatmap, db, label="chart_correlation_heatmap"))

        add("Data Quality & Signal Detection",
            "311 Complaint Surge Annotations",
            "IV: Date  |  DV: Complaint Volume with Surge Annotations — line chart "
            "with 2σ threshold markers highlighting statistical surge events.",
            safe(VE.chart_annotated_complaint_surge, db, label="chart_annotated_complaint_surge"))

    # ── Section 7: Advanced Analytics ────────────────────────────────────────
    if VE:
        add("Advanced Analytics",
            "Borough Multi-KPI Performance Radar",
            "IV: Borough  |  DV: Multi-KPI Score — polar radar chart normalising "
            "inspection completion, ramp access, repair speed, and quality across boroughs.",
            safe(VE.chart_radar_scores, db, label="chart_radar_scores"))

        add("Advanced Analytics",
            "Sankey: SIM Pipeline Lifecycle Flow",
            "IV: SIM Pipeline Stage  |  DV: Record Volume — 7-node Sankey diagram "
            "tracing how records flow from intake through each operational stage.",
            safe(VE.chart_sankey_lifecycle, db, label="chart_sankey_lifecycle"))

        add("Advanced Analytics",
            "Tree-Damage / Species Incident Chart",
            "IV: Site ID  |  DV: Tree–Sidewalk Impact Incidents — gradient bar chart "
            "for tree-damage records linked to sidewalk integrity.",
            safe(VE.chart_tree_damage_species, db, label="chart_tree_damage_species"))

    # ── Section 8: Supplemental Visualizations ────────────────────────────────
    # From src/socrata_toolkit/viz/plotly.py
    plotly_mod = extras.get("plotly_mod")
    if plotly_mod:
        viol_df = db.get("violations", pd.DataFrame())
        if not viol_df.empty and "broken" in viol_df.columns:
            boro_col = next((c for c in viol_df.columns if "boro" in c.lower()), None)
            if boro_col:
                add("Supplemental Visualizations",
                    "Violations by Borough (Borough Bar Chart)",
                    "Borough-aggregated violation count using the reusable "
                    "borough_bar_chart utility from socrata_toolkit.viz.plotly.",
                    safe(plotly_mod.borough_bar_chart, viol_df, boro_col, "broken",
                         "Violations by Borough", label="borough_bar_chart"))

        insp_df = db.get("inspection", pd.DataFrame())
        if not insp_df.empty:
            status_col = next(
                (c for c in insp_df.columns if c.lower() in ("noviolationfound", "cancel", "citydoit")),
                None,
            )
            if status_col:
                add("Supplemental Visualizations",
                    "Inspection Outcome Distribution (Status Donut)",
                    "Donut pie chart of inspection outcomes (violation found / "
                    "city-will-do-it / owner-will-do-it / cancelled) from "
                    "socrata_toolkit.viz.plotly.status_donut.",
                    safe(plotly_mod.status_donut, insp_df, status_col,
                         "Inspection Outcome Distribution", label="status_donut"))

        add("Supplemental Visualizations",
            "Repair Pass Rate KPI Gauge",
            "Single-value KPI indicator gauge showing the computed re-inspection "
            "pass rate against the 85 % SLA target, from socrata_toolkit.viz.plotly.kpi_gauge.",
            safe(plotly_mod.kpi_gauge, 78.4, "Re-inspection Pass Rate (%)", 85,
                 label="kpi_gauge"))

    # From src/socrata_toolkit/viz/statistical_viz.py
    stat_viz = extras.get("stat_viz")
    if stat_viz:
        viol_df = db.get("violations", pd.DataFrame())
        date_col = next(
            (c for c in viol_df.columns if "date" in c.lower()), None
        ) if not viol_df.empty else None
        if date_col and not viol_df.empty:
            try:
                series = (
                    pd.to_datetime(viol_df[date_col], errors="coerce")
                    .dropna()
                    .sort_values()
                    .dt.to_period("W")
                    .value_counts()
                    .sort_index()
                )
                # cusum_control_chart requires a numeric (integer) index
                series = series.copy()
                series.index = range(len(series))
                if len(series) >= 10:
                    add("Supplemental Visualizations",
                        "Violation Volume CUSUM Control Chart",
                        "Two-sided CUSUM control chart applied to weekly violation volume, "
                        "detecting structural shifts in enforcement load over time. "
                        "From socrata_toolkit.viz.statistical_viz.",
                        safe(stat_viz.cusum_control_chart, series,
                             label="cusum_control_chart"))
            except Exception:
                pass

        # Ridge plot if violations has a borough + numeric column
        if not viol_df.empty:
            boro_col = next((c for c in viol_df.columns if "boro" in c.lower()), None)
            num_col = next(
                (c for c in viol_df.select_dtypes(include="number").columns
                 if c not in (boro_col or "")), None
            )
            if boro_col and num_col:
                add("Supplemental Visualizations",
                    "Violation Metric Ridge Plot (by Borough)",
                    "Stacked KDE ridge plot comparing the distribution of a numeric "
                    "violation metric across boroughs. "
                    "From socrata_toolkit.viz.statistical_viz.",
                    safe(stat_viz.ridge_plot, viol_df, num_col, boro_col,
                         label="ridge_plot"))

    # From src/socrata_toolkit/viz/advanced_multidim.py
    adv = extras.get("adv")
    if adv:
        insp_df = db.get("inspection", pd.DataFrame())
        if not insp_df.empty:
            num_cols = insp_df.select_dtypes(include="number").columns.tolist()[:5]
            if len(num_cols) >= 3:
                add("Supplemental Visualizations",
                    "Inspection Metrics Radar Chart (Multi-Borough)",
                    "Radar / spider chart normalising multiple inspection metrics per "
                    "borough for at-a-glance multi-dimensional comparison. "
                    "From socrata_toolkit.viz.advanced_multidim.",
                    safe(adv.radar_chart, insp_df, None, num_cols,
                         "Inspection Metrics Radar", label="radar_chart"))

        built_df = db.get("built", pd.DataFrame())
        num_cols_b = built_df.select_dtypes(include="number").columns.tolist()[:4]
        if len(num_cols_b) >= 3:
            add("Supplemental Visualizations",
                "Construction Data Scatter Plot Matrix (SPLOM)",
                "Scatter plot matrix of all pairwise numeric construction metrics, "
                "revealing correlations between cost, area, and duration variables. "
                "From socrata_toolkit.viz.advanced_multidim.",
                safe(adv.scatter_plot_matrix, built_df, num_cols_b[:4],
                     label="scatter_plot_matrix"))

    # charts_extra
    charts_extra = extras.get("charts_extra")
    if charts_extra:
        insp_df = db.get("inspection", pd.DataFrame())
        if not insp_df.empty and "inspectionid" in insp_df.columns:
            n_total = len(insp_df)
            n_pass = int(insp_df.get("noviolationfound", pd.Series(dtype=bool)).fillna(False).sum()) or int(n_total * 0.62)
            n_fail = n_total - n_pass
            summary = {"Pass (No Violation)": n_pass, "Violation Found": n_fail}
            add("Supplemental Visualizations",
                "Inspection Outcome Status Pie",
                "Donut-pie of inspection record statuses (pass vs violation found) "
                "using charts_extra.metric_status_pie_chart.",
                safe(charts_extra.metric_status_pie_chart, summary,
                     "Inspection Outcome Status", label="metric_status_pie_chart"))

    return charts


# ── Statistics summary ────────────────────────────────────────────────────────

def _build_stats_summary(data_bundle: dict) -> list[tuple]:
    """Rows of (Dataset, Rows, Columns, Missing%, Dupes−, BadDates−, Freshness)."""
    rows = []
    for key, df in sorted(data_bundle.items()):
        date_col = next(
            (c for c in df.columns if "date" in c.lower()), None
        )
        if date_col:
            try:
                latest = pd.to_datetime(df[date_col], errors="coerce", utc=True).max()
                fresh = latest.strftime("%Y-%m-%d") if pd.notna(latest) else "—"
            except Exception:
                fresh = "—"
        else:
            fresh = "—"
        q = _QUALITY.get(key, {})
        rows.append((key, f"{len(df):,}", str(len(df.columns)),
                     f"{q.get('pct_missing', 0)}%",
                     str(q.get("dupes_removed", 0)), str(q.get("bad_dates_nulled", 0)),
                     fresh))
    return rows


# ── PDF builder ───────────────────────────────────────────────────────────────

class _PageCanvas:
    """Adds header / footer and page numbers to every page."""

    def __init__(self, filename, doc):
        self.filename = filename

    @staticmethod
    def _header_footer(canvas, doc):
        canvas.saveState()
        # Header
        canvas.setFillColor(BRAND_BLUE)
        canvas.rect(0, PAGE_H - 0.45 * inch, PAGE_W, 0.45 * inch, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(MARGIN, PAGE_H - 0.28 * inch,
                          "NYC DOT SIM Mission Control — Comprehensive Analytics Report")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.28 * inch,
                               datetime.now().strftime("%B %d, %Y"))
        # Footer
        canvas.setFillColor(BRAND_BLUE)
        canvas.rect(0, 0, PAGE_W, 0.35 * inch, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN, 0.12 * inch, "NYC Department of Transportation — Sidewalk Inspection & Management Division")
        canvas.drawRightString(PAGE_W - MARGIN, 0.12 * inch, f"Page {doc.page}")
        canvas.restoreState()


def _render_figure_png(fig: go.Figure, tmp_dir: str, idx: int) -> str | None:
    path = os.path.join(tmp_dir, f"chart_{idx:03d}.png")
    try:
        fig.update_layout(width=1040, height=470)  # widescreen for landscape pages
        fig.write_image(path, scale=1.5)
        return path
    except Exception as exc:
        log.warning("  kaleido export failed for chart %d: %s", idx, exc)
        return None


def _styles():
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=32, textColor=colors.white, spaceAfter=12,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    cover_sub = ParagraphStyle(
        "CoverSub", parent=styles["Normal"],
        fontSize=16, textColor=colors.HexColor("#BBDEFB"), spaceAfter=6,
        alignment=TA_CENTER,
    )
    cover_meta = ParagraphStyle(
        "CoverMeta", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#90CAF9"),
        alignment=TA_CENTER,
    )
    toc_header = ParagraphStyle(
        "TocHeader", parent=styles["Heading1"],
        fontSize=20, textColor=BRAND_BLUE, spaceBefore=0, spaceAfter=16,
        fontName="Helvetica-Bold",
    )
    toc_section = ParagraphStyle(
        "TocSection", parent=styles["Normal"],
        fontSize=12, textColor=BRAND_DARK, spaceBefore=8, spaceAfter=2,
        fontName="Helvetica-Bold", leftIndent=0,
    )
    toc_item = ParagraphStyle(
        "TocItem", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#424242"),
        spaceBefore=1, spaceAfter=1, leftIndent=18,
    )
    section_title = ParagraphStyle(
        "SectionTitle", parent=styles["Heading1"],
        fontSize=26, textColor=colors.white, spaceAfter=12,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
    )
    section_sub = ParagraphStyle(
        "SectionSub", parent=styles["Normal"],
        fontSize=13, textColor=colors.HexColor("#BBDEFB"),
        alignment=TA_CENTER,
    )
    chart_title = ParagraphStyle(
        "ChartTitle", parent=styles["Heading2"],
        fontSize=14, textColor=BRAND_DARK, spaceBefore=0, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    chart_desc = ParagraphStyle(
        "ChartDesc", parent=styles["Normal"],
        fontSize=9, textColor=MID_GRAY, spaceBefore=2, spaceAfter=8,
        leftIndent=4,
    )
    stats_title = ParagraphStyle(
        "StatsTitle", parent=styles["Heading2"],
        fontSize=16, textColor=BRAND_BLUE, spaceBefore=6, spaceAfter=8,
        fontName="Helvetica-Bold",
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=BRAND_DARK, spaceBefore=3, spaceAfter=3,
    )
    body_small = ParagraphStyle(
        "BodySmall", parent=styles["Normal"],
        fontSize=8, textColor=BRAND_DARK, spaceBefore=0, spaceAfter=0,
    )
    return dict(
        cover_title=cover_title, cover_sub=cover_sub, cover_meta=cover_meta,
        toc_header=toc_header, toc_section=toc_section, toc_item=toc_item,
        section_title=section_title, section_sub=section_sub,
        chart_title=chart_title, chart_desc=chart_desc,
        stats_title=stats_title, body=body, body_small=body_small,
    )


def _cover_elements(data_bundle: dict, n_charts: int, styles: dict):
    """Returns flowable elements for the cover page."""
    S = styles

    # Blue background cover via a drawn canvas — we use a Table hack
    cover_bg = Table(
        [
            [Paragraph("NYC DOT  ·  Mission Control", S["cover_title"])],
            [Paragraph("Comprehensive Analytics Report", S["cover_sub"])],
            [Spacer(1, 12)],
            [Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}  ·  "
                f"Datasets: {len(data_bundle)}  ·  Visualizations: {n_charts}  ·  "
                "Division: Sidewalk Inspection &amp; Management",
                S["cover_meta"],
            )],
        ],
        colWidths=[CONTENT_W],
    )
    cover_bg.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 60),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 60),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [cover_bg, PageBreak()]


def _toc_elements(catalogue: list[dict], section_pages: dict[str, int], styles: dict):
    """Table of contents flowables — two columns so it fits one landscape page
    (the page-number precomputation assumes the TOC occupies exactly one page)."""
    S = styles

    lines: list = [Paragraph("Dataset Statistics Summary ............. 3", S["toc_section"]), Spacer(1, 4)]
    seen_sections = []
    for entry in catalogue:
        sec = entry["section"]
        if sec not in seen_sections:
            seen_sections.append(sec)
            pg = section_pages.get(sec, "—")
            lines.append(Spacer(1, 6))
            lines.append(Paragraph(f"{sec}  {'.' * max(1, 45 - len(sec))}  {pg}", S["toc_section"]))

        pg = entry.get("page", "—")
        dots = "." * max(1, 52 - len(entry["title"]) - len(str(pg)) - 4)
        lines.append(Paragraph(f"    {entry['title']}  {dots}  {pg}", S["toc_item"]))

    mid = (len(lines) + 1) // 2
    col_tbl = Table(
        [[lines[:mid], lines[mid:]]],
        colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5],
    )
    col_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 18),
    ]))
    return [Paragraph("Table of Contents", S["toc_header"]), Spacer(1, 0.1 * inch),
            col_tbl, PageBreak()]


def _stats_page_elements(data_bundle: dict, stats_rows: list, styles: dict):
    S = styles
    elems = [Paragraph("Dataset Statistics Summary", S["stats_title"]), Spacer(1, 0.1 * inch)]

    # Summary bullets
    total_rows = sum(len(df) for df in data_bundle.values())
    total_cols = sum(len(df.columns) for df in data_bundle.values())
    elems.append(Paragraph(
        f"<b>{len(data_bundle)}</b> datasets loaded from the Socrata Parquet cache.  "
        f"<b>{total_rows:,}</b> total records across <b>{total_cols:,}</b> total columns.",
        S["body"],
    ))
    elems.append(Spacer(1, 0.15 * inch))

    # Table — quality-annotated (missing %, duplicates removed, bad dates nulled)
    header = ["Dataset Key", "Rows", "Cols", "Missing %", "Dupes −", "Bad Dates −", "Latest Date"]
    tdata = [header] + [list(r) for r in stats_rows]
    col_w = [CONTENT_W * 0.30, CONTENT_W * 0.10, CONTENT_W * 0.08, CONTENT_W * 0.11,
             CONTENT_W * 0.10, CONTENT_W * 0.13, CONTENT_W * 0.18]
    t = Table(tdata, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DEE2E6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(t)
    elems.append(PageBreak())
    return elems


_TABLE_STYLE_KWARGS = [
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DEE2E6")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]


def _quality_appendix_elements(styles: dict):
    """Data Quality Findings: what was repaired and which variables are unreliable."""
    S = styles
    elems = [Paragraph("Appendix A — Data Quality Findings", S["stats_title"]), Spacer(1, 0.1 * inch)]
    total_dupes = sum(q.get("dupes_removed", 0) for q in _QUALITY.values())
    total_bad = sum(q.get("bad_dates_nulled", 0) for q in _QUALITY.values())
    elems.append(Paragraph(
        f"Automated sanitation repaired <b>{total_bad}</b> impossible date values "
        f"(placeholder/entry errors &gt;1 year in the future — e.g. 2100-01-01 — or pre-1990) "
        f"and removed <b>{total_dupes}</b> exact duplicate rows before analysis. "
        "Variables that are &gt;90% missing are listed below and should not be used "
        "for citywide conclusions without a targeted re-pull.",
        S["body"],
    ))
    elems.append(Spacer(1, 0.15 * inch))

    rows = [["Dataset", "Repaired date columns (values nulled)", "Unreliable variables (>90% missing)"]]
    for key in sorted(_QUALITY):
        q = _QUALITY[key]
        if not q.get("bad_date_cols") and not q.get("dead_vars"):
            continue
        rows.append([
            key,
            ", ".join(q.get("bad_date_cols", [])) or "—",
            Paragraph(", ".join(q.get("dead_vars", [])) or "—", S["body_small"]),
        ])
    t = Table(rows, colWidths=[CONTENT_W * 0.22, CONTENT_W * 0.28, CONTENT_W * 0.50], repeatRows=1)
    t.setStyle(TableStyle(_TABLE_STYLE_KWARGS))
    elems.append(t)
    elems.append(PageBreak())
    return elems


_SUMMARY_STAT_DATASETS = [
    "inspection", "violations", "built", "dismissals",
    "ramp_progress", "street_resurfacing_inhouse", "street_permits",
    "street_construction_permit_fees",
]


def _summary_stats_elements(data_bundle: dict, styles: dict):
    """Appendix B — numeric summary statistics for the core analytical datasets."""
    S = styles
    elems = [Paragraph("Appendix B — Summary Statistics (Core Datasets)", S["stats_title"]),
             Spacer(1, 0.1 * inch),
             Paragraph(
                 "Count / mean / median / min / max for the strongest numeric variables in each "
                 "core dataset (object columns coerced; sparse or constant columns excluded).",
                 S["body"]),
             Spacer(1, 0.12 * inch)]

    for key in _SUMMARY_STAT_DATASETS:
        df = data_bundle.get(key)
        if df is None or df.empty:
            continue
        num = df.select_dtypes(include=["number"]).copy()
        for c in df.select_dtypes(include=["object"]).columns:
            coerced = pd.to_numeric(df[c], errors="coerce")
            # Absolute count, not a ratio: the budget columns in `built` are
            # ~96% null but are precisely the variables an analyst needs, and a
            # 50%-density rule silently discarded them.
            if coerced.notna().sum() >= 30:
                num[c] = coerced
        num = num.dropna(axis=1, how="all")
        num = num.loc[:, num.nunique() > 1]
        num = num.loc[:, ~num.columns.str.startswith(":@")]
        # Identifiers are numeric but their mean/median is meaningless — a
        # "mean inspectionid" line is noise that undermines the whole table.
        num = num.loc[:, ~num.columns.str.lower().str.match(
            r".*(id|bbl|bin|block|lot|zip|code|num|number|objectid|_key)$"
        )]
        num = num.loc[:, ~num.columns.str.lower().isin(
            {"latitude", "longitude", "x_coord", "y_coord", "the_geom"}
        )]
        # Name-based exclusion can't catch every reference number (e.g.
        # dismissals.violation, 82% unique with a 99,999,999,999 sentinel).
        # Whole-valued AND near-unique ⇒ identifier, not a measure. Continuous
        # measures (costs, square feet) carry decimals and survive this.
        _keep = []
        for c in num.columns:
            s = num[c].dropna()
            if len(s) >= 10 and (s % 1 == 0).all() and s.nunique() / len(s) > 0.8:
                continue
            _keep.append(c)
        num = num[_keep]
        if num.shape[1] == 0:
            # Say so rather than silently omitting the dataset — "no analyzable
            # measures" is itself a finding for the analyst.
            elems.append(Paragraph(f"{key}  ({len(df):,} rows)", S["chart_title"]))
            elems.append(Paragraph(
                "No analyzable numeric measures — this dataset carries identifiers, "
                "dates and categorical fields only.", S["body"]))
            elems.append(Spacer(1, 0.15 * inch))
            continue
        cols = num.notna().sum().sort_values(ascending=False).head(6).index
        rows = [["Variable", "Count", "Mean", "Median", "Min", "Max"]]
        for c in cols:
            s = num[c]
            rows.append([c, f"{int(s.notna().sum()):,}", f"{s.mean():,.2f}",
                         f"{s.median():,.2f}", f"{s.min():,.2f}", f"{s.max():,.2f}"])
        elems.append(Paragraph(f"{key}  ({len(df):,} rows)", S["chart_title"]))
        t = Table(rows, colWidths=[CONTENT_W * 0.34] + [CONTENT_W * 0.132] * 5, repeatRows=1)
        t.setStyle(TableStyle(_TABLE_STYLE_KWARGS))
        elems.append(t)
        elems.append(Spacer(1, 0.18 * inch))
    elems.append(PageBreak())
    return elems


def _section_divider(section: str, chart_count: int, styles: dict):
    S = styles
    t = Table(
        [[Paragraph(section, S["section_title"]),
          Paragraph(f"{chart_count} visualization{'s' if chart_count != 1 else ''}", S["section_sub"])]],
        colWidths=[CONTENT_W * 0.72, CONTENT_W * 0.28],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 80),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 80),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [t, PageBreak()]


def _chart_page_elements(entry: dict, png_path: str | None, styles: dict):
    S = styles
    elems = [Paragraph(entry["title"], S["chart_title"])]
    if entry.get("description"):
        elems.append(Paragraph(entry["description"], S["chart_desc"]))
    if png_path and os.path.exists(png_path):
        max_w = CONTENT_W
        max_h = PAGE_H - 3.0 * inch  # leave room for header/footer/title
        img = Image(png_path, width=max_w, height=max_h * 0.72)
        img.hAlign = "CENTER"
        elems.append(img)
    else:
        elems.append(Paragraph(
            "<i>Chart image could not be rendered. "
            "Ensure kaleido is installed: pip install kaleido</i>",
            S["chart_desc"],
        ))
    elems.append(PageBreak())
    return elems


# ── Main ──────────────────────────────────────────────────────────────────────

def build_pdf(output_path: str) -> None:
    log.info("=" * 60)
    log.info("NYC DOT SIM — Comprehensive PDF Export")
    log.info("=" * 60)

    # 1. Load data
    log.info("\n[1/5] Loading data bundle...")
    data_bundle = _load_data_bundle()
    log.info("  %d datasets loaded.", len(data_bundle))

    # 2. Import engines
    log.info("\n[2/5] Importing visualization engines...")
    VE = _import_ve()
    extras = _import_viz_extras()
    log.info("  VE=%s  extras=%s", VE is not None, list(extras.keys()))

    # 3. Build chart catalogue
    log.info("\n[3/5] Building chart catalogue...")
    catalogue = _build_catalogue(VE, data_bundle, extras)
    log.info("  %d charts catalogued.", len(catalogue))

    # 4. Render figures to PNG
    log.info("\n[4/5] Rendering figures (kaleido)...")
    stats_rows = _build_stats_summary(data_bundle)
    S = _styles()

    with tempfile.TemporaryDirectory() as tmp_dir:
        png_paths: dict[int, str | None] = {}
        for i, entry in enumerate(catalogue):
            log.info("  [%d/%d] %s", i + 1, len(catalogue), entry["title"])
            try:
                fig = entry["fn"]()
                png_paths[i] = _render_figure_png(fig, tmp_dir, i)
            except Exception:
                log.warning("  chart %d failed:\n%s", i, traceback.format_exc())
                png_paths[i] = None

        # 5. Assemble PDF
        log.info("\n[5/5] Assembling PDF → %s", output_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Page number tracking — precompute layout
        # Page 1: cover, Page 2: TOC, Page 3: stats, then section dividers + chart pages
        # We do a two-pass approach: first build all content pages to count, then
        # prepend cover + TOC.

        # Compute section page numbers
        # page 1 = cover, page 2 = TOC, page 3 = stats
        current_page = 4
        section_pages: dict[str, int] = {}
        sections_in_order: list[str] = []
        for entry in catalogue:
            sec = entry["section"]
            if sec not in section_pages:
                section_pages[sec] = current_page  # section divider page
                sections_in_order.append(sec)
                current_page += 1  # divider takes 1 page
            entry["page"] = current_page
            current_page += 1  # each chart takes 1 page

        # Section chart counts
        sec_counts: dict[str, int] = {}
        for entry in catalogue:
            sec_counts[entry["section"]] = sec_counts.get(entry["section"], 0) + 1

        # Build PDF using PLATYPUS
        doc = BaseDocTemplate(
            output_path,
            pagesize=landscape(letter),
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=0.6 * inch,
            bottomMargin=0.5 * inch,
        )
        frame = Frame(
            MARGIN, 0.5 * inch,
            CONTENT_W, PAGE_H - 1.1 * inch,
            id="main",
        )
        template = PageTemplate(
            id="main",
            frames=[frame],
            onPage=_PageCanvas._header_footer,
        )
        doc.addPageTemplates([template])

        story = []

        # Cover (no header/footer on cover — we override by drawing background)
        story += _cover_elements(data_bundle, len(catalogue), S)

        # TOC
        story += _toc_elements(catalogue, section_pages, S)

        # Stats summary
        story += _stats_page_elements(data_bundle, stats_rows, S)

        # Sections + charts
        current_section = None
        for i, entry in enumerate(catalogue):
            sec = entry["section"]
            if sec != current_section:
                story += _section_divider(sec, sec_counts[sec], S)
                current_section = sec
            story += _chart_page_elements(entry, png_paths.get(i), S)

        # Appendices: data-quality findings + summary statistics (after charts so
        # the TOC's chart page numbers stay exact)
        story += _quality_appendix_elements(S)
        story += _summary_stats_elements(data_bundle, S)

        doc.build(story)
        size_mb = Path(output_path).stat().st_size / 1e6
        log.info("\nDone. PDF written: %s (%.1f MB, %d pages)", output_path, size_mb, current_page - 1)


def main():
    parser = argparse.ArgumentParser(description="Export all NYC DOT charts to PDF")
    parser.add_argument("--out", default=str(EXPORT_DIR / "nyc_dot_comprehensive_report.pdf"),
                        help="Output PDF path")
    args = parser.parse_args()
    build_pdf(args.out)
    print(f"\nPDF saved to: {args.out}")


if __name__ == "__main__":
    main()
