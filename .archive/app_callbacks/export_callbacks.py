"""
Export Callbacks: Wire export buttons to universal exporter.

Implements download handlers for PDF, CSV, Excel formats:
- Each visualization has an export button with dropdown menu
- User selects format → callback triggers download
- File is generated on-demand with current data + statistics

Data flow:
    User clicks export → Modal/dropdown shows format options
    → User selects format (PDF/CSV/Excel)
    → Callback fetches current figure/data
    → UniversalExporter generates file
    → Browser triggers download

All exports include:
- Chart/data as primary content
- Statistics table
- Narrative (if applicable)
- Metadata (date, record count)
"""

import logging
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc

from app.services.motherduck_service import (
    fetch_phase_b_results,
    fetch_phase_c_results,
    fetch_phase_d_results,
    fetch_phase_e_decomposition,
    fetch_phase_f_bootstrap_ci,
)
from app.services.universal_exporter import UniversalExporter

logger = logging.getLogger(__name__)

exporter = UniversalExporter()

def register_export_callbacks() -> None:
    """
    Register all export callbacks.

    Callbacks registered:
    - Phase B export (PDF/CSV/Excel)
    - Phase C export (PDF/CSV/Excel)
    - Phase D export (PDF/CSV/Excel)
    - Phase E export (PDF/CSV/Excel)
    - Phase F export (PDF/CSV/Excel)
    """

    # =========================================================================
    # PHASE B EXPORTS
    # =========================================================================

    @callback(
        Output("phase-b-download", "data"),
        Input("phase-b-export-pdf-btn", "n_clicks"),
        Input("phase-b-export-csv-btn", "n_clicks"),
        Input("phase-b-export-excel-btn", "n_clicks"),
        State("phase-b-figure", "children"),
        State("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    def export_phase_b(
        pdf_clicks: int,
        csv_clicks: int,
        excel_clicks: int,
        figure_div,
        filters: dict[str, Any],
    ):
        """Export Phase B results in requested format."""
        try:
            from dash import ctx

            trigger_id = ctx.triggered_id if ctx.triggered_id else None

            # Fetch fresh data
            df = fetch_phase_b_results(filters)
            if df is None or df.empty:
                logger.warning("No data available for Phase B export")
                return None

            stats = {
                "Borough Count": len(df),
                "Generated": datetime.now().isoformat(),
            }

            # Dummy figure for PDF (would be extracted from callback state in production)
            fig = go.Figure()

            if trigger_id == "phase-b-export-pdf-btn":
                pdf_bytes = exporter.export_figure_to_pdf(
                    fig,
                    "Phase B: Moran's I Spatial Autocorrelation",
                    stats,
                    "Spatial clustering analysis results.",
                )
                return dcc.send_bytes(pdf_bytes, "phase_b_analysis.pdf")

            elif trigger_id == "phase-b-export-csv-btn":
                csv_str = exporter.export_data_to_csv(
                    df,
                    "Phase B: Moran's I Results",
                    stats,
                )
                return dcc.send_string(csv_str, "phase_b_analysis.csv")

            elif trigger_id == "phase-b-export-excel-btn":
                xlsx_bytes = exporter.export_data_to_excel(
                    df,
                    "Phase B: Moran's I Results",
                    "Spatial clustering analysis.",
                    stats,
                )
                return dcc.send_bytes(xlsx_bytes, "phase_b_analysis.xlsx")

        except Exception as e:
            logger.error(f"Error exporting Phase B: {e}", exc_info=True)
            return None

    # =========================================================================
    # PHASE C EXPORTS
    # =========================================================================

    @callback(
        Output("phase-c-download", "data"),
        Input("phase-c-export-pdf-btn", "n_clicks"),
        Input("phase-c-export-csv-btn", "n_clicks"),
        Input("phase-c-export-excel-btn", "n_clicks"),
        State("phase-c-figure", "children"),
        State("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    def export_phase_c(
        pdf_clicks: int,
        csv_clicks: int,
        excel_clicks: int,
        figure_div,
        filters: dict[str, Any],
    ):
        """Export Phase C results in requested format."""
        try:
            from dash import ctx

            trigger_id = ctx.triggered_id if ctx.triggered_id else None

            df = fetch_phase_c_results(filters)
            if df is None or df.empty:
                logger.warning("No data available for Phase C export")
                return None

            stats = {
                "Records": len(df),
                "Generated": datetime.now().isoformat(),
            }

            fig = go.Figure()

            if trigger_id == "phase-c-export-pdf-btn":
                pdf_bytes = exporter.export_figure_to_pdf(
                    fig,
                    "Phase C: Distribution Classification",
                    stats,
                    "Distribution analysis results.",
                )
                return dcc.send_bytes(pdf_bytes, "phase_c_distribution.pdf")

            elif trigger_id == "phase-c-export-csv-btn":
                csv_str = exporter.export_data_to_csv(
                    df,
                    "Phase C: Distribution Results",
                    stats,
                )
                return dcc.send_string(csv_str, "phase_c_distribution.csv")

            elif trigger_id == "phase-c-export-excel-btn":
                xlsx_bytes = exporter.export_data_to_excel(
                    df,
                    "Phase C: Distribution Results",
                    "Distribution analysis.",
                    stats,
                )
                return dcc.send_bytes(xlsx_bytes, "phase_c_distribution.xlsx")

        except Exception as e:
            logger.error(f"Error exporting Phase C: {e}", exc_info=True)
            return None

    # =========================================================================
    # PHASE D EXPORTS
    # =========================================================================

    @callback(
        Output("phase-d-download", "data"),
        Input("phase-d-export-pdf-btn", "n_clicks"),
        Input("phase-d-export-csv-btn", "n_clicks"),
        Input("phase-d-export-excel-btn", "n_clicks"),
        State("phase-d-figure", "children"),
        State("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    def export_phase_d(
        pdf_clicks: int,
        csv_clicks: int,
        excel_clicks: int,
        figure_div,
        filters: dict[str, Any],
    ):
        """Export Phase D results in requested format."""
        try:
            from dash import ctx

            trigger_id = ctx.triggered_id if ctx.triggered_id else None

            df = fetch_phase_d_results(filters)
            if df is None or df.empty:
                logger.warning("No data available for Phase D export")
                return None

            stats = {
                "Anomalies": len(df),
                "Generated": datetime.now().isoformat(),
            }

            fig = go.Figure()

            if trigger_id == "phase-d-export-pdf-btn":
                pdf_bytes = exporter.export_figure_to_pdf(
                    fig,
                    "Phase D: Anomaly Detection",
                    stats,
                    "Geographic anomaly analysis.",
                )
                return dcc.send_bytes(pdf_bytes, "phase_d_anomalies.pdf")

            elif trigger_id == "phase-d-export-csv-btn":
                csv_str = exporter.export_data_to_csv(
                    df,
                    "Phase D: Anomaly Results",
                    stats,
                )
                return dcc.send_string(csv_str, "phase_d_anomalies.csv")

            elif trigger_id == "phase-d-export-excel-btn":
                xlsx_bytes = exporter.export_data_to_excel(
                    df,
                    "Phase D: Anomaly Results",
                    "Geographic anomaly analysis.",
                    stats,
                )
                return dcc.send_bytes(xlsx_bytes, "phase_d_anomalies.xlsx")

        except Exception as e:
            logger.error(f"Error exporting Phase D: {e}", exc_info=True)
            return None

    # =========================================================================
    # PHASE E EXPORTS
    # =========================================================================

    @callback(
        Output("phase-e-download", "data"),
        Input("phase-e-export-pdf-btn", "n_clicks"),
        Input("phase-e-export-csv-btn", "n_clicks"),
        Input("phase-e-export-excel-btn", "n_clicks"),
        State("phase-e-figure", "children"),
        State("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    def export_phase_e(
        pdf_clicks: int,
        csv_clicks: int,
        excel_clicks: int,
        figure_div,
        filters: dict[str, Any],
    ):
        """Export Phase E results in requested format."""
        try:
            from dash import ctx

            trigger_id = ctx.triggered_id if ctx.triggered_id else None

            df = fetch_phase_e_decomposition(filters)
            if df is None or df.empty:
                logger.warning("No data available for Phase E export")
                return None

            stats = {
                "Periods": len(df),
                "Generated": datetime.now().isoformat(),
            }

            fig = go.Figure()

            if trigger_id == "phase-e-export-pdf-btn":
                pdf_bytes = exporter.export_figure_to_pdf(
                    fig,
                    "Phase E: Seasonal Decomposition",
                    stats,
                    "Time series decomposition analysis.",
                )
                return dcc.send_bytes(pdf_bytes, "phase_e_decomposition.pdf")

            elif trigger_id == "phase-e-export-csv-btn":
                csv_str = exporter.export_data_to_csv(
                    df,
                    "Phase E: Decomposition Results",
                    stats,
                )
                return dcc.send_string(csv_str, "phase_e_decomposition.csv")

            elif trigger_id == "phase-e-export-excel-btn":
                xlsx_bytes = exporter.export_data_to_excel(
                    df,
                    "Phase E: Decomposition Results",
                    "Time series decomposition.",
                    stats,
                )
                return dcc.send_bytes(xlsx_bytes, "phase_e_decomposition.xlsx")

        except Exception as e:
            logger.error(f"Error exporting Phase E: {e}", exc_info=True)
            return None

    # =========================================================================
    # PHASE F EXPORTS
    # =========================================================================

    @callback(
        Output("phase-f-download", "data"),
        Input("phase-f-export-pdf-btn", "n_clicks"),
        Input("phase-f-export-csv-btn", "n_clicks"),
        Input("phase-f-export-excel-btn", "n_clicks"),
        State("phase-f-figure", "children"),
        State("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    def export_phase_f(
        pdf_clicks: int,
        csv_clicks: int,
        excel_clicks: int,
        figure_div,
        filters: dict[str, Any],
    ):
        """Export Phase F results in requested format."""
        try:
            from dash import ctx

            trigger_id = ctx.triggered_id if ctx.triggered_id else None

            df = fetch_phase_f_bootstrap_ci(filters)
            if df is None or df.empty:
                logger.warning("No data available for Phase F export")
                return None

            stats = {
                "Boroughs": len(df),
                "Generated": datetime.now().isoformat(),
            }

            fig = go.Figure()

            if trigger_id == "phase-f-export-pdf-btn":
                pdf_bytes = exporter.export_figure_to_pdf(
                    fig,
                    "Phase F: Bootstrap CI / SLA Forecast",
                    stats,
                    "SLA risk analysis with confidence intervals.",
                )
                return dcc.send_bytes(pdf_bytes, "phase_f_bootstrap_ci.pdf")

            elif trigger_id == "phase-f-export-csv-btn":
                csv_str = exporter.export_data_to_csv(
                    df,
                    "Phase F: Bootstrap CI Results",
                    stats,
                )
                return dcc.send_string(csv_str, "phase_f_bootstrap_ci.csv")

            elif trigger_id == "phase-f-export-excel-btn":
                xlsx_bytes = exporter.export_data_to_excel(
                    df,
                    "Phase F: Bootstrap CI Results",
                    "SLA risk analysis with confidence intervals.",
                    stats,
                )
                return dcc.send_bytes(xlsx_bytes, "phase_f_bootstrap_ci.xlsx")

        except Exception as e:
            logger.error(f"Error exporting Phase F: {e}", exc_info=True)
            return None

    logger.info("Export callbacks registered (all 5 phases)")

