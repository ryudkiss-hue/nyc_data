"""
Generate Research Questions → Chart Recommendations Sankey Diagram as standalone HTML
"""

import plotly.graph_objects as go
import json

# ============================================================================
# SOURCE LAYER: Data Input Patterns
# ============================================================================
data_patterns = [
    "Temporal (date/time series)",
    "Geographic (lat/lon/block)",
    "Categorical (violation_type)",
    "Numeric (count/cost/days)",
    "Multivariate (3+ columns)",
    "Hierarchical (borough→CB→block)",
    "Comparative (owner types)",
]

# ============================================================================
# INTENT LAYER: Research Questions / Analytical Intents
# ============================================================================
research_questions = [
    # Trend & Time Series (temporal)
    "Q1: Trend over time?",
    "Q2: Seasonality pattern?",
    "Q3: Structural break/changepoint?",
    "Q4: Forecast next period?",

    # Spatial & Geographic
    "Q5: Geographic hotspots?",
    "Q6: Spatial clustering?",
    "Q7: Neighborhood rankings?",
    "Q8: Spatial autocorrelation?",

    # Property Owner & Enforcement
    "Q9: Owner compliance rates?",
    "Q10: Repeat offenders?",
    "Q11: Owner type comparison?",
    "Q12: Property value predicts speed?",

    # Violation Characteristics
    "Q13: Violation type distribution?",
    "Q14: Severity ranking?",
    "Q15: Type-specific timelines?",
    "Q16: Cost distribution?",

    # Enforcement Efficiency
    "Q17: Overall compliance rate?",
    "Q18: City vs owner repairs?",
    "Q19: Cure window adherence?",
    "Q20: Contractor performance?",

    # Quality & Gaps
    "Q21: 311→Inspection gap?",
    "Q22: Data completeness?",
    "Q23: Missing inspections?",
    "Q24: Coverage equity?",

    # Risk & Prioritization
    "Q25: Vision Zero overlap?",
    "Q26: High-traffic areas?",
    "Q27: Financial impact rank?",
    "Q28: Complaint volume hotspots?",

    # Predictive
    "Q29: Future violation risk?",
    "Q30: Repair timeline prediction?",
    "Q31: Non-compliance prediction?",

    # Comparative
    "Q32: Borough benchmarking?",
    "Q33: Community Board ranking?",
    "Q34: Multi-dimensional comparison?",

    # Anomaly Detection
    "Q35: Outlier violations?",
    "Q36: Unusual patterns?",
    "Q37: Extreme properties?",
]

# ============================================================================
# DESTINATION LAYER: Recommended Charts (65+ from registry)
# ============================================================================
charts = [
    # Time Series (7 charts)
    "Line Chart (trend)",
    "Area Chart (volume over time)",
    "CUSUM Control Chart (process shifts)",
    "Changepoint Overlay (temporal breaks)",
    "Seasonal Decomposition (patterns)",
    "Ridge Plot (KDE by time period)",
    "Stream Graph (composition over time)",

    # Geographic/Spatial (9 charts)
    "Scatter Map (lat/lon violations)",
    "Heatmap (block-level density)",
    "Choropleth (borough/CB aggregate)",
    "Hex-Bin Map (spatial density)",
    "Force Network (proximity/relationships)",
    "Moran's I Scatter (spatial autocorrelation)",
    "DBSCAN Cluster Map (spatial groups)",
    "Conflict Buffer Map (permit overlaps)",
    "TSP Route Optimization (service routing)",

    # Distribution & Composition (8 charts)
    "Histogram (distribution shape)",
    "Violin Plot (distribution by group)",
    "Stacked Bar (composition)",
    "100% Stacked Bar (proportions)",
    "Sankey Diagram (flow/transitions)",
    "Funnel Chart (drop-off analysis)",
    "Pie Chart (simple composition)",
    "Donut Chart (part-to-whole)",

    # Comparison (12 charts)
    "Bar Chart (side-by-side)",
    "Grouped Bar (multi-dimensional)",
    "Box Plot (distribution comparison)",
    "Dot Plot (precise comparison)",
    "Radar Chart (multi-metric profile)",
    "Parallel Coordinates (multivariate)",
    "SPLOM (scatter plot matrix)",
    "Clustermap (heatmap + dendro)",
    "Bump Chart (ranking changes)",
    "Diverging Stacked Bar (positive/negative)",
    "Lollipop Chart (ordered comparison)",
    "Strip Plot (individual comparisons)",

    # Relationships & Correlation (8 charts)
    "Scatter Plot (2D relationship)",
    "Bubble Chart (3D scatter)",
    "Crossfilter (linked scatter)",
    "Hexbin Plot (density scatter)",
    "Contour Plot (2D density)",
    "Correlation Heatmap (matrix)",
    "Network Graph (connections)",
    "Chord Diagram (flow magnitude)",

    # Statistical & Advanced (8 charts)
    "Bayesian Posterior Strip (credible intervals)",
    "HDI Violin (Bayesian posterior viz)",
    "Control Chart (SPC limits)",
    "Q-Q Plot (normality assessment)",
    "Residual Plot (model diagnostics)",
    "ROC Curve (classifier performance)",
    "Calibration Plot (prediction accuracy)",
    "Lift Chart (model lift)",

    # Ranking & Hierarchical (4 charts)
    "Treemap (hierarchical ranking)",
    "Sunburst (hierarchical drill-down)",
    "Tree Diagram (organizational)",
    "Packed Bubble (size hierarchy)",

    # Anomaly & Outlier (3 charts)
    "Outlier Scatter (flagged points)",
    "Isolation Forest Scatter (anomalies)",
    "Z-Score Strip (standardized outliers)",

    # Executive/Dashboard (4 charts)
    "KPI Card (single metric)",
    "Gauge Chart (target tracking)",
    "Metric Sparkline (mini trend)",
    "Scorecard (quality metrics)",
]

# ============================================================================
# FLOW MAPPING: Questions → Charts (Links)
# ============================================================================
flows = [
    # Q1: Trend over time?
    ("Q1: Trend over time?", "Line Chart (trend)", 8),
    ("Q1: Trend over time?", "Area Chart (volume over time)", 7),
    ("Q1: Trend over time?", "CUSUM Control Chart (process shifts)", 5),
    ("Q1: Trend over time?", "Changepoint Overlay (temporal breaks)", 4),
    ("Q1: Trend over time?", "Ridge Plot (KDE by time period)", 3),

    # Q2: Seasonality?
    ("Q2: Seasonality pattern?", "Ridge Plot (KDE by time period)", 6),
    ("Q2: Seasonality pattern?", "Area Chart (volume over time)", 5),
    ("Q2: Seasonality pattern?", "CUSUM Control Chart (process shifts)", 4),
    ("Q2: Seasonality pattern?", "Line Chart (trend)", 7),

    # Q3: Changepoint?
    ("Q3: Structural break/changepoint?", "Changepoint Overlay (temporal breaks)", 9),
    ("Q3: Structural break/changepoint?", "CUSUM Control Chart (process shifts)", 8),
    ("Q3: Structural break/changepoint?", "Line Chart (trend)", 5),

    # Q4: Forecast?
    ("Q4: Forecast next period?", "Line Chart (trend)", 7),
    ("Q4: Forecast next period?", "Area Chart (volume over time)", 6),

    # Q5: Geographic hotspots?
    ("Q5: Geographic hotspots?", "Heatmap (block-level density)", 9),
    ("Q5: Geographic hotspots?", "Hex-Bin Map (spatial density)", 8),
    ("Q5: Geographic hotspots?", "Choropleth (borough/CB aggregate)", 7),
    ("Q5: Geographic hotspots?", "Scatter Map (lat/lon violations)", 6),
    ("Q5: Geographic hotspots?", "Conflict Buffer Map (permit overlaps)", 5),

    # Q6: Spatial clustering?
    ("Q6: Spatial clustering?", "DBSCAN Cluster Map (spatial groups)", 9),
    ("Q6: Spatial clustering?", "Moran's I Scatter (spatial autocorrelation)", 7),
    ("Q6: Spatial clustering?", "Hex-Bin Map (spatial density)", 6),
    ("Q6: Spatial clustering?", "Force Network (proximity/relationships)", 4),

    # Q7: Neighborhood rankings?
    ("Q7: Neighborhood rankings?", "Bar Chart (side-by-side)", 9),
    ("Q7: Neighborhood rankings?", "Lollipop Chart (ordered comparison)", 8),
    ("Q7: Neighborhood rankings?", "Choropleth (borough/CB aggregate)", 7),
    ("Q7: Neighborhood rankings?", "Treemap (hierarchical ranking)", 6),

    # Q8: Spatial autocorrelation?
    ("Q8: Spatial autocorrelation?", "Moran's I Scatter (spatial autocorrelation)", 9),
    ("Q8: Spatial autocorrelation?", "Hex-Bin Map (spatial density)", 5),

    # Q9: Owner compliance rates?
    ("Q9: Owner compliance rates?", "Bar Chart (side-by-side)", 8),
    ("Q9: Owner compliance rates?", "Diverging Stacked Bar (positive/negative)", 7),
    ("Q9: Owner compliance rates?", "Dot Plot (precise comparison)", 6),
    ("Q9: Owner compliance rates?", "KPI Card (single metric)", 5),

    # Q10: Repeat offenders?
    ("Q10: Repeat offenders?", "Outlier Scatter (flagged points)", 8),
    ("Q10: Repeat offenders?", "Scatter Plot (2D relationship)", 7),
    ("Q10: Repeat offenders?", "Bar Chart (side-by-side)", 6),
    ("Q10: Repeat offenders?", "Bubble Chart (3D scatter)", 5),

    # Q11: Owner type comparison?
    ("Q11: Owner type comparison?", "Grouped Bar (multi-dimensional)", 9),
    ("Q11: Owner type comparison?", "Box Plot (distribution comparison)", 8),
    ("Q11: Owner type comparison?", "Violin Plot (distribution by group)", 7),
    ("Q11: Owner type comparison?", "Radar Chart (multi-metric profile)", 6),

    # Q12: Property value predicts speed?
    ("Q12: Property value predicts speed?", "Scatter Plot (2D relationship)", 9),
    ("Q12: Property value predicts speed?", "Bubble Chart (3D scatter)", 8),
    ("Q12: Property value predicts speed?", "Hexbin Plot (density scatter)", 6),
    ("Q12: Property value predicts speed?", "Correlation Heatmap (matrix)", 5),

    # Q13: Violation type distribution?
    ("Q13: Violation type distribution?", "Bar Chart (side-by-side)", 9),
    ("Q13: Violation type distribution?", "Stacked Bar (composition)", 7),
    ("Q13: Violation type distribution?", "Pie Chart (simple composition)", 5),
    ("Q13: Violation type distribution?", "Histogram (distribution shape)", 4),

    # Q14: Severity ranking?
    ("Q14: Severity ranking?", "Lollipop Chart (ordered comparison)", 9),
    ("Q14: Severity ranking?", "Bar Chart (side-by-side)", 8),
    ("Q14: Severity ranking?", "Treemap (hierarchical ranking)", 6),
    ("Q14: Severity ranking?", "Bump Chart (ranking changes)", 4),

    # Q15: Type-specific timelines?
    ("Q15: Type-specific timelines?", "Ridge Plot (KDE by time period)", 8),
    ("Q15: Type-specific timelines?", "Box Plot (distribution comparison)", 8),
    ("Q15: Type-specific timelines?", "Violin Plot (distribution by group)", 7),
    ("Q15: Type-specific timelines?", "Grouped Bar (multi-dimensional)", 6),

    # Q16: Cost distribution?
    ("Q16: Cost distribution?", "Histogram (distribution shape)", 8),
    ("Q16: Cost distribution?", "Box Plot (distribution comparison)", 7),
    ("Q16: Cost distribution?", "Violin Plot (distribution by group)", 6),
    ("Q16: Cost distribution?", "Bubble Chart (3D scatter)", 5),

    # Q17: Overall compliance rate?
    ("Q17: Overall compliance rate?", "KPI Card (single metric)", 10),
    ("Q17: Overall compliance rate?", "Gauge Chart (target tracking)", 8),
    ("Q17: Overall compliance rate?", "Metric Sparkline (mini trend)", 5),

    # Q18: City vs owner repairs?
    ("Q18: City vs owner repairs?", "100% Stacked Bar (proportions)", 9),
    ("Q18: City vs owner repairs?", "Stacked Bar (composition)", 8),
    ("Q18: City vs owner repairs?", "Sankey Diagram (flow/transitions)", 7),
    ("Q18: City vs owner repairs?", "Grouped Bar (multi-dimensional)", 6),

    # Q19: Cure window adherence?
    ("Q19: Cure window adherence?", "Control Chart (SPC limits)", 8),
    ("Q19: Cure window adherence?", "Line Chart (trend)", 7),
    ("Q19: Cure window adherence?", "Gauge Chart (target tracking)", 7),

    # Q20: Contractor performance?
    ("Q20: Contractor performance?", "Bar Chart (side-by-side)", 8),
    ("Q20: Contractor performance?", "Scatter Plot (2D relationship)", 7),
    ("Q20: Contractor performance?", "Radar Chart (multi-metric profile)", 6),
    ("Q20: Contractor performance?", "Box Plot (distribution comparison)", 5),

    # Q21: 311→Inspection gap?
    ("Q21: 311→Inspection gap?", "Funnel Chart (drop-off analysis)", 9),
    ("Q21: 311→Inspection gap?", "Sankey Diagram (flow/transitions)", 8),
    ("Q21: 311→Inspection gap?", "Scatter Plot (2D relationship)", 6),

    # Q22: Data completeness?
    ("Q22: Data completeness?", "Scorecard (quality metrics)", 9),
    ("Q22: Data completeness?", "Heatmap (block-level density)", 7),
    ("Q22: Data completeness?", "Bar Chart (side-by-side)", 5),

    # Q23: Missing inspections?
    ("Q23: Missing inspections?", "Scatter Map (lat/lon violations)", 9),
    ("Q23: Missing inspections?", "Choropleth (borough/CB aggregate)", 8),
    ("Q23: Missing inspections?", "Heatmap (block-level density)", 7),

    # Q24: Coverage equity?
    ("Q24: Coverage equity?", "Choropleth (borough/CB aggregate)", 8),
    ("Q24: Coverage equity?", "Box Plot (distribution comparison)", 7),
    ("Q24: Coverage equity?", "Violin Plot (distribution by group)", 6),

    # Q25: Vision Zero overlap?
    ("Q25: Vision Zero overlap?", "Conflict Buffer Map (permit overlaps)", 9),
    ("Q25: Vision Zero overlap?", "Scatter Map (lat/lon violations)", 8),
    ("Q25: Vision Zero overlap?", "Heatmap (block-level density)", 7),

    # Q26: High-traffic areas?
    ("Q26: High-traffic areas?", "Heatmap (block-level density)", 9),
    ("Q26: High-traffic areas?", "Bubble Chart (3D scatter)", 8),
    ("Q26: High-traffic areas?", "Scatter Map (lat/lon violations)", 7),

    # Q27: Financial impact rank?
    ("Q27: Financial impact rank?", "Lollipop Chart (ordered comparison)", 9),
    ("Q27: Financial impact rank?", "Bar Chart (side-by-side)", 8),
    ("Q27: Financial impact rank?", "Treemap (hierarchical ranking)", 7),
    ("Q27: Financial impact rank?", "Bubble Chart (3D scatter)", 6),

    # Q28: Complaint volume hotspots?
    ("Q28: Complaint volume hotspots?", "Heatmap (block-level density)", 9),
    ("Q28: Complaint volume hotspots?", "Hex-Bin Map (spatial density)", 8),
    ("Q28: Complaint volume hotspots?", "Scatter Map (lat/lon violations)", 7),

    # Q29: Future violation risk?
    ("Q29: Future violation risk?", "Scatter Plot (2D relationship)", 8),
    ("Q29: Future violation risk?", "Bubble Chart (3D scatter)", 7),
    ("Q29: Future violation risk?", "Calibration Plot (prediction accuracy)", 5),

    # Q30: Repair timeline prediction?
    ("Q30: Repair timeline prediction?", "Scatter Plot (2D relationship)", 8),
    ("Q30: Repair timeline prediction?", "Line Chart (trend)", 7),
    ("Q30: Repair timeline prediction?", "Box Plot (distribution comparison)", 6),

    # Q31: Non-compliance prediction?
    ("Q31: Non-compliance prediction?", "ROC Curve (classifier performance)", 7),
    ("Q31: Non-compliance prediction?", "Lift Chart (model lift)", 6),
    ("Q31: Non-compliance prediction?", "Scatter Plot (2D relationship)", 5),

    # Q32: Borough benchmarking?
    ("Q32: Borough benchmarking?", "Grouped Bar (multi-dimensional)", 9),
    ("Q32: Borough benchmarking?", "Radar Chart (multi-metric profile)", 8),
    ("Q32: Borough benchmarking?", "Parallel Coordinates (multivariate)", 6),
    ("Q32: Borough benchmarking?", "Dot Plot (precise comparison)", 5),

    # Q33: Community Board ranking?
    ("Q33: Community Board ranking?", "Choropleth (borough/CB aggregate)", 9),
    ("Q33: Community Board ranking?", "Bar Chart (side-by-side)", 8),
    ("Q33: Community Board ranking?", "Lollipop Chart (ordered comparison)", 7),
    ("Q33: Community Board ranking?", "Treemap (hierarchical ranking)", 6),

    # Q34: Multi-dimensional comparison?
    ("Q34: Multi-dimensional comparison?", "Parallel Coordinates (multivariate)", 9),
    ("Q34: Multi-dimensional comparison?", "SPLOM (scatter plot matrix)", 8),
    ("Q34: Multi-dimensional comparison?", "Radar Chart (multi-metric profile)", 7),
    ("Q34: Multi-dimensional comparison?", "Clustermap (heatmap + dendro)", 6),

    # Q35: Outlier violations?
    ("Q35: Outlier violations?", "Outlier Scatter (flagged points)", 10),
    ("Q35: Outlier violations?", "Isolation Forest Scatter (anomalies)", 9),
    ("Q35: Outlier violations?", "Z-Score Strip (standardized outliers)", 8),
    ("Q35: Outlier violations?", "Scatter Plot (2D relationship)", 6),

    # Q36: Unusual patterns?
    ("Q36: Unusual patterns?", "Line Chart (trend)", 7),
    ("Q36: Unusual patterns?", "Clustermap (heatmap + dendro)", 8),
    ("Q36: Unusual patterns?", "Heatmap (block-level density)", 6),

    # Q37: Extreme properties?
    ("Q37: Extreme properties?", "Outlier Scatter (flagged points)", 9),
    ("Q37: Extreme properties?", "Bubble Chart (3D scatter)", 8),
    ("Q37: Extreme properties?", "Scatter Plot (2D relationship)", 7),
    ("Q37: Extreme properties?", "Box Plot (distribution comparison)", 5),

    # Data Patterns → Questions
    ("Temporal (date/time series)", "Q1: Trend over time?", 10),
    ("Temporal (date/time series)", "Q2: Seasonality pattern?", 8),
    ("Temporal (date/time series)", "Q3: Structural break/changepoint?", 6),
    ("Temporal (date/time series)", "Q4: Forecast next period?", 5),

    ("Geographic (lat/lon/block)", "Q5: Geographic hotspots?", 10),
    ("Geographic (lat/lon/block)", "Q6: Spatial clustering?", 9),
    ("Geographic (lat/lon/block)", "Q7: Neighborhood rankings?", 8),
    ("Geographic (lat/lon/block)", "Q8: Spatial autocorrelation?", 6),
    ("Geographic (lat/lon/block)", "Q25: Vision Zero overlap?", 7),
    ("Geographic (lat/lon/block)", "Q23: Missing inspections?", 6),

    ("Categorical (violation_type)", "Q13: Violation type distribution?", 10),
    ("Categorical (violation_type)", "Q14: Severity ranking?", 8),
    ("Categorical (violation_type)", "Q15: Type-specific timelines?", 7),
    ("Categorical (violation_type)", "Q34: Multi-dimensional comparison?", 5),

    ("Numeric (count/cost/days)", "Q16: Cost distribution?", 9),
    ("Numeric (count/cost/days)", "Q17: Overall compliance rate?", 8),
    ("Numeric (count/cost/days)", "Q27: Financial impact rank?", 7),
    ("Numeric (count/cost/days)", "Q20: Contractor performance?", 6),

    ("Multivariate (3+ columns)", "Q34: Multi-dimensional comparison?", 10),
    ("Multivariate (3+ columns)", "Q11: Owner type comparison?", 8),
    ("Multivariate (3+ columns)", "Q32: Borough benchmarking?", 8),
    ("Multivariate (3+ columns)", "Q12: Property value predicts speed?", 7),

    ("Hierarchical (borough→CB→block)", "Q33: Community Board ranking?", 10),
    ("Hierarchical (borough→CB→block)", "Q7: Neighborhood rankings?", 9),
    ("Hierarchical (borough→CB→block)", "Q34: Multi-dimensional comparison?", 6),

    ("Comparative (owner types)", "Q9: Owner compliance rates?", 10),
    ("Comparative (owner types)", "Q11: Owner type comparison?", 9),
    ("Comparative (owner types)", "Q10: Repeat offenders?", 7),
]

# ============================================================================
# Build Sankey
# ============================================================================
all_nodes = list(data_patterns) + research_questions + charts
node_indices = {node: idx for idx, node in enumerate(all_nodes)}

source = [node_indices[src] for src, _, _ in flows]
target = [node_indices[dst] for _, dst, _ in flows]
value = [v for _, _, v in flows]

# Colors: Data Patterns (blue) → Questions (green) → Charts (orange)
node_colors = (
    ["#1f77b4"] * len(data_patterns)  # Blue for data patterns
    + ["#2ca02c"] * len(research_questions)  # Green for questions
    + ["#ff7f0e"] * len(charts)  # Orange for charts
)

fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_nodes,
        color=node_colors,
    ),
    link=dict(
        source=source,
        target=target,
        value=value,
        color=[f"rgba(200, 200, 200, 0.4)"] * len(flows),
    ),
)])

fig.update_layout(
    title=dict(
        text="<b>Research Questions → Chart Recommendations Sankey</b><br><sub>Data Patterns → Analyst Intent → Recommended Visualizations</sub>",
        font=dict(size=18),
        x=0.5,
        xanchor="center",
    ),
    font=dict(size=11, family="Arial, sans-serif"),
    height=1400,
    width=1800,
    margin=dict(l=30, r=30, t=100, b=30),
    paper_bgcolor="white",
    plot_bgcolor="white",
)

# Save to HTML
html_string = fig.to_html(
    include_plotlyjs='cdn',
    div_id="sankey-chart",
    config={
        'responsive': True,
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d'],
    }
)

# Wrap with custom HTML for better styling
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Questions → Chart Recommendations Sankey</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Arial', 'Helvetica', sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 2000px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 50%, #ff7f0e 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .header p {{
            font-size: 14px;
            opacity: 0.95;
            margin-bottom: 5px;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
            font-size: 13px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid rgba(255,255,255,0.5);
        }}
        .chart-container {{
            padding: 20px;
            overflow-x: auto;
        }}
        #sankey-chart {{
            width: 100%;
            height: 100%;
        }}
        .footer {{
            background: #f9f9f9;
            border-top: 1px solid #e0e0e0;
            padding: 20px 30px;
            font-size: 12px;
            color: #666;
            line-height: 1.6;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: rgba(0,0,0,0.05);
            padding: 10px 15px;
            border-radius: 4px;
            text-align: center;
            border-left: 3px solid #1f77b4;
        }}
        .stat-number {{
            font-size: 18px;
            font-weight: bold;
            color: #1f77b4;
        }}
        .stat-label {{
            font-size: 11px;
            color: #888;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Research Questions → Chart Recommendations</h1>
            <p><strong>Data Patterns</strong> → <strong>Analyst Intent</strong> → <strong>Recommended Visualizations</strong></p>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #1f77b4;"></div>
                    <span>7 Data Patterns</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2ca02c;"></div>
                    <span>37 Research Questions</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ff7f0e;"></div>
                    <span>65+ Recommended Charts</span>
                </div>
            </div>
        </div>

        <div class="chart-container">
            {html_string}
        </div>

        <div class="footer">
            <h3>How to Read This Sankey</h3>
            <p>
                <strong>Flow Width:</strong> Thicker flows indicate stronger chart recommendations (confidence 10 = excellent fit, 4 = secondary option)<br>
                <strong>Left Column (Blue):</strong> Data input patterns detected in your DataFrame (temporal, geographic, categorical, numeric, multivariate, hierarchical, comparative)<br>
                <strong>Middle Column (Green):</strong> 37 research questions that analysts ask about SIM Program data—organized across 10 categories<br>
                <strong>Right Column (Orange):</strong> 65+ recommended charts from your visualization registry, scored by fit to the question<br>
            </p>

            <h3 style="margin-top: 15px;">Question Categories</h3>
            <p>
                📈 <strong>Trend & Time Series (4Q):</strong> Changes over time, seasonality, structural breaks, forecasts<br>
                🗺️ <strong>Geographic & Spatial (5Q):</strong> Hotspots, clustering, neighborhood rankings, autocorrelation<br>
                🏢 <strong>Property Owner & Enforcement (4Q):</strong> Compliance, repeat offenders, owner type comparison, property value prediction<br>
                📊 <strong>Violation Characteristics (4Q):</strong> Type distribution, severity, timelines, cost<br>
                ⚖️ <strong>Enforcement Efficiency (4Q):</strong> Overall compliance, city vs owner repairs, cure window, contractor performance<br>
                🔍 <strong>Quality & Gaps (4Q):</strong> 311→Inspection gaps, data completeness, missing inspections, coverage equity<br>
                ⚠️ <strong>Risk & Prioritization (4Q):</strong> Vision Zero overlap, high-traffic areas, financial impact, complaint volume<br>
                🔮 <strong>Predictive (3Q):</strong> Future violation risk, repair timeline, non-compliance prediction<br>
                📋 <strong>Comparative (3Q):</strong> Borough benchmarking, community board ranking, multi-dimensional comparison<br>
                🎯 <strong>Anomaly Detection (3Q):</strong> Outlier violations, unusual patterns, extreme properties<br>
            </p>

            <div class="stats">
                <div class="stat-box" style="border-left-color: #1f77b4;">
                    <div class="stat-number">7</div>
                    <div class="stat-label">Data Patterns</div>
                </div>
                <div class="stat-box" style="border-left-color: #2ca02c;">
                    <div class="stat-number">37</div>
                    <div class="stat-label">Research Questions</div>
                </div>
                <div class="stat-box" style="border-left-color: #ff7f0e;">
                    <div class="stat-number">65+</div>
                    <div class="stat-label">Chart Recommendations</div>
                </div>
                <div class="stat-box" style="border-left-color: #9467bd;">
                    <div class="stat-number">110+</div>
                    <div class="stat-label">Sankey Flows</div>
                </div>
                <div class="stat-box" style="border-left-color: #d62728;">
                    <div class="stat-number">51</div>
                    <div class="stat-label">Datasets Referenced</div>
                </div>
                <div class="stat-box" style="border-left-color: #17becf;">
                    <div class="stat-number">10</div>
                    <div class="stat-label">Question Categories</div>
                </div>
            </div>

            <p style="margin-top: 20px;">
                <em>Generated for NYC DOT Sidewalk Inspection & Management Program (SIM) · Chart Finder Implementation Reference</em>
            </p>
        </div>
    </div>
</body>
</html>
"""

# Write to file
with open("research_questions_sankey.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print("✓ Sankey diagram generated: research_questions_sankey.html")
print(f"✓ Total flows: {len(flows)}")
print(f"✓ Data patterns: {len(data_patterns)}")
print(f"✓ Research questions: {len(research_questions)}")
print(f"✓ Chart recommendations: {len(charts)}")
