import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
from pathlib import Path
import os
import sys

def generate_report(pdf_path: str = "docs/reports/verification_report.pdf"):
    Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Title Page
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 100, "Manhattan Mission Control")
    c.setFont("Helvetica", 16)
    c.drawString(50, height - 140, "Comprehensive Verification & Dashboard Export")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 180, "Generated directly from L2 Parquet Data Cache")
    c.showPage()

    datasets = {
        'Sidewalk Inspections': 'data/local_db/socrata_cache/inspection.parquet',
        'Violations Ledger': 'data/local_db/socrata_cache/violations.parquet',
        '311 Service Requests': 'data/local_db/socrata_cache/complaints_311.parquet',
        'Capital Projects': 'data/local_db/socrata_cache/capital_blocks.parquet'
    }

    for name, path in datasets.items():
        if not os.path.exists(path):
            continue
            
        df = pd.read_parquet(path)
        
        y_pos = height - 50
        
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, y_pos, f"Dashboard: {name}")
        y_pos -= 30
        
        c.setFont("Helvetica", 12)
        c.drawString(50, y_pos, f"Summary Statistics:")
        y_pos -= 20
        c.drawString(60, y_pos, f"Total Records: {len(df):,}")
        y_pos -= 20
        c.drawString(60, y_pos, f"Total Attributes: {len(df.columns)}")
        y_pos -= 30
        
        # Try to make a visualization if it makes sense
        fig = None
        try:
            if name == 'Sidewalk Inspections' and 'noviolationfound' in df.columns:
                counts = df['noviolationfound'].value_counts().reset_index()
                fig = px.pie(counts, names='noviolationfound', values='count', title=f'{name} - Violation Found Distribution')
            elif name == 'Violations Ledger' and 'violationstatus' in df.columns:
                counts = df['violationstatus'].value_counts().reset_index()
                fig = px.bar(counts, x='violationstatus', y='count', title=f'{name} - Violation Status')
            elif name == '311 Service Requests' and 'status' in df.columns:
                counts = df['status'].value_counts().reset_index()
                fig = px.bar(counts, x='status', y='count', title=f'{name} - Complaint Status')
            elif name == 'Capital Projects' and 'project_type' in df.columns:
                counts = df['project_type'].value_counts().reset_index()
                fig = px.pie(counts, names='project_type', values='count', title=f'{name} - Project Types')
        except Exception as e:
            print(f"Skipping visualization for {name}: {e}")
            
        if fig:
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    fig.write_image(tmp.name, engine="kaleido", width=800, height=500)
                    img = ImageReader(tmp.name)
                    c.drawImage(img, 50, y_pos - 350, width=500, height=312)
                    y_pos -= 380
            except Exception as e:
                print(f"Failed to render image for {name}: {e}")
                
        c.showPage()

    c.save()
    print(f"Exported PDF to {pdf_path}")

if __name__ == "__main__":
    generate_report()
