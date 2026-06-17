"""
Universal Exporter: Multi-format export system for visualizations and reports.

Supports 3 export formats for all 73 charts + 5 narratives:
1. PDF - ReportLab: Chart image + statistics table
2. CSV - Pandas: Data + statistics as CSV
3. Excel - openpyxl: Data sheet + statistics sheet with formatting

Usage:
    from app.services.universal_exporter import UniversalExporter
    exporter = UniversalExporter()

    # Export chart to PDF
    pdf_bytes = exporter.export_figure_to_pdf(
        figure=go.Figure(),
        title="Phase B: Moran's I Analysis",
        statistics={"Morans_I": 0.342, "p_value": 0.05}
    )

    # Export data to CSV
    csv_str = exporter.export_data_to_csv(
        df=pd.DataFrame(),
        title="Phase C: Distribution"
    )

    # Export to Excel
    xlsx_bytes = exporter.export_data_to_excel(
        df=pd.DataFrame(),
        narrative="Key insight text",
        title="Phase E: Decomposition"
    )
"""

import io
import logging
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

class UniversalExporter:
    """Multi-format exporter for visualizations and data."""

    def __init__(self):
        """Initialize exporter with dependencies check."""
        self._check_dependencies()

    @staticmethod
    def _check_dependencies() -> None:
        """Verify required libraries are installed."""
        missing = []
        for lib in ["reportlab", "openpyxl"]:
            try:
                __import__(lib)
            except ImportError:
                missing.append(lib)

        if missing:
            logger.warning(f"Optional libraries missing: {missing}. Some exports may be limited.")

    def export_figure_to_pdf(
        self,
        figure: go.Figure,
        title: str,
        statistics: dict[str, Any],
        narrative: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Export Plotly figure to PDF with statistics table.

        Args:
            figure: Plotly Figure object
            title: Report title
            statistics: Dict of statistics to display
            narrative: Optional narrative text

        Returns:
            bytes: PDF file content (or None on error)

        Format:
            ┌──────────────────────────┐
            │ Title                    │
            │ [Chart Image]            │
            ├──────────────────────────┤
            │ Statistics               │
            │ Key1: Value1             │
            │ Key2: Value2             │
            │ ...                      │
            ├──────────────────────────┤
            │ Narrative (if provided)  │
            └──────────────────────────┘
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            from reportlab.platypus import (
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            logger.error("ReportLab not installed. Install with: pip install reportlab")
            return None

        try:
            # Convert figure to image (PNG)
            img_bytes = figure.to_image(format="png", width=700, height=500)
            if img_bytes is None:
                logger.warning("Could not convert figure to PNG. Skipping chart in PDF.")
                img_bytes = b""

            # Create PDF buffer
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Add title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#212529'),
                spaceAfter=30,
            )
            elements.append(Paragraph(title, title_style))

            # Add chart image
            if img_bytes:
                try:
                    from reportlab.platypus import Image
                    img_file = io.BytesIO(img_bytes)
                    img = Image(img_file, width=6*inch, height=4*inch)
                    elements.append(img)
                    elements.append(Spacer(1, 0.3*inch))
                except Exception as e:
                    logger.warning(f"Could not embed image: {e}")

            # Add statistics table
            if statistics:
                stat_data = [["Metric", "Value"]]
                for key, value in statistics.items():
                    if isinstance(value, float):
                        formatted = f"{value:.4f}"
                    else:
                        formatted = str(value)
                    stat_data.append([str(key), formatted])

                stat_table = Table(stat_data, colWidths=[3*inch, 3*inch])
                stat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(stat_table)

            # Add narrative if provided
            if narrative:
                elements.append(Spacer(1, 0.2*inch))
                narrative_style = ParagraphStyle(
                    'Narrative',
                    parent=styles['BodyText'],
                    fontSize=10,
                    textColor=colors.HexColor('#495057'),
                )
                elements.append(Paragraph("<b>Key Insight</b>", narrative_style))
                elements.append(Paragraph(narrative[:500], narrative_style))

            # Build PDF
            doc.build(elements)
            pdf_buffer.seek(0)
            logger.info(f"PDF exported successfully: {title}")
            return pdf_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}", exc_info=True)
            return None

    def export_data_to_csv(
        self,
        df: pd.DataFrame,
        title: str,
        statistics: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Export data to CSV format.

        Args:
            df: DataFrame to export
            title: Report title (included as comment)
            statistics: Optional statistics dict

        Returns:
            str: CSV content (or None on error)

        Format:
            # Report Title
            # Generated: 2026-06-11 14:30:00
            # Records: 100
            #
            column1,column2,column3,...
            value1,value2,value3,...
            ...
        """
        try:
            csv_buffer = io.StringIO()

            # Add header comments
            csv_buffer.write(f"# {title}\n")
            csv_buffer.write(f"# Generated: {datetime.now().isoformat()}\n")
            csv_buffer.write(f"# Records: {len(df)}\n")

            # Add statistics as comments
            if statistics:
                csv_buffer.write("#\n# Statistics:\n")
                for key, value in statistics.items():
                    csv_buffer.write(f"# {key}: {value}\n")

            csv_buffer.write("#\n")

            # Add data
            df.to_csv(csv_buffer, index=False)
            logger.info(f"CSV exported successfully: {title} ({len(df)} rows)")
            return csv_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            return None

    def export_data_to_excel(
        self,
        df: pd.DataFrame,
        title: str,
        narrative: Optional[str] = None,
        statistics: Optional[dict[str, Any]] = None,
    ) -> Optional[bytes]:
        """
        Export data to Excel format with multiple sheets.

        Args:
            df: DataFrame to export
            title: Report title
            narrative: Optional narrative text (goes in separate sheet)
            statistics: Optional statistics dict (goes in separate sheet)

        Returns:
            bytes: XLSX file content (or None on error)

        Format:
            Sheet "Data": Full DataFrame
            Sheet "Statistics": Statistics table (if provided)
            Sheet "Narrative": Narrative text (if provided)
            Sheet "Summary": Title, date, record count
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils.dataframe import dataframe_to_rows
        except ImportError:
            logger.error("openpyxl not installed. Install with: pip install openpyxl")
            return None

        try:
            wb = Workbook()
            wb.remove(wb.active)  # Remove default sheet

            # Summary sheet
            ws_summary = wb.create_sheet("Summary", 0)
            ws_summary["A1"] = title
            ws_summary["A1"].font = Font(size=16, bold=True)
            ws_summary["A3"] = "Generated"
            ws_summary["B3"] = datetime.now().isoformat()
            ws_summary["A4"] = "Records"
            ws_summary["B4"] = len(df)

            # Data sheet
            ws_data = wb.create_sheet("Data", 1)
            for row_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                for col_idx, value in enumerate(row, 1):
                    ws_data.cell(row=row_idx, column=col_idx, value=value)

            # Format header row
            header_fill = PatternFill(start_color="007bff", end_color="007bff", fill_type="solid")
            header_font = Font(color="ffffff", bold=True)
            for cell in ws_data[1]:
                cell.fill = header_fill
                cell.font = header_font

            # Statistics sheet (if provided)
            if statistics:
                ws_stats = wb.create_sheet("Statistics", 2)
                ws_stats["A1"] = "Metric"
                ws_stats["B1"] = "Value"
                for row_idx, (key, value) in enumerate(statistics.items(), 2):
                    ws_stats[f"A{row_idx}"] = key
                    ws_stats[f"B{row_idx}"] = value

            # Narrative sheet (if provided)
            if narrative:
                ws_narrative = wb.create_sheet("Narrative", 3)
                ws_narrative["A1"] = "Key Insight"
                ws_narrative["A2"] = narrative

            # Auto-size columns
            for ws in wb.sheetnames:
                ws_obj = wb[ws]
                for column in ws_obj.columns:
                    max_length = max(len(str(cell.value or "")) for cell in column)
                    ws_obj.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)

            # Export to bytes
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            logger.info(f"Excel exported successfully: {title}")
            return excel_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}", exc_info=True)
            return None

    def export_report_multiformat(
        self,
        figure: go.Figure,
        df: pd.DataFrame,
        title: str,
        narrative: str,
        statistics: dict[str, Any],
    ) -> dict[str, Optional[bytes]]:
        """
        Export a complete report in all 3 formats.

        Args:
            figure: Plotly Figure
            df: DataFrame
            title: Report title
            narrative: Narrative text
            statistics: Statistics dict

        Returns:
            dict: {"pdf": bytes, "csv": str, "xlsx": bytes}

        Usage:
            exports = exporter.export_report_multiformat(
                figure=fig,
                df=df,
                title="Phase B Analysis",
                narrative="Key insight...",
                statistics={"morans_i": 0.342}
            )
            # Save to files
            with open("report.pdf", "wb") as f:
                f.write(exports["pdf"])
        """
        return {
            "pdf": self.export_figure_to_pdf(figure, title, statistics, narrative),
            "csv": self.export_data_to_csv(df, title, statistics),
            "xlsx": self.export_data_to_excel(df, title, narrative, statistics),
        }
