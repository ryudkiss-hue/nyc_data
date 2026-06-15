"""
Research Questions → Chart Recommendations Sankey Diagram

This module generates an interactive Sankey chart mapping:
- Data Input Patterns (columns, types, temporal structure)
  ↓
- Analyst Research Questions / Intents
  ↓
- Recommended Charts (65+ visualizations)

Use for understanding Chart Finder's question-to-chart routing logic.
"""

import plotly.graph_objects as go
from typing import Dict, List, Tuple


def generate_research_questions_sankey() -> go.Figure:
    """
    Create comprehensive Sankey showing research questions → chart recommendations.
    """

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
        # Q1: Trend over time? → Line, Area, CUSUM, Changepoint, Ridge, Stream
        ("Q1: Trend over time?", "Line Chart (trend)", 8),
        ("Q1: Trend over time?", "Area Chart (volume over time)", 7),
        ("Q1: Trend over time?", "CUSUM Control Chart (process shifts)", 5),
        ("Q1: Trend over time?", "Changepoint Overlay (temporal breaks)", 4),
        ("Q1: Trend over time?", "Ridge Plot (KDE by time period)", 3),

        # Q2: Seasonality? → Seasonal Decomp, Ridge, CUSUM
        ("Q2: Seasonality pattern?", "Ridge Plot (KDE by time period)", 6),
        ("Q2: Seasonality pattern?", "Area Chart (volume over time)", 5),
        ("Q2: Seasonality pattern?", "CUSUM Control Chart (process shifts)", 4),
        ("Q2: Seasonality pattern?", "Line Chart (trend)", 7),

        # Q3: Changepoint? → Changepoint, CUSUM, Line
        ("Q3: Structural break/changepoint?", "Changepoint Overlay (temporal breaks)", 9),
        ("Q3: Structural break/changepoint?", "CUSUM Control Chart (process shifts)", 8),
        ("Q3: Structural break/changepoint?", "Line Chart (trend)", 5),

        # Q4: Forecast? → Line, Area
        ("Q4: Forecast next period?", "Line Chart (trend)", 7),
        ("Q4: Forecast next period?", "Area Chart (volume over time)", 6),

        # Q5: Geographic hotspots? → Heatmap, Choropleth, HexBin, Scatter Map
        ("Q5: Geographic hotspots?", "Heatmap (block-level density)", 9),
        ("Q5: Geographic hotspots?", "Hex-Bin Map (spatial density)", 8),
        ("Q5: Geographic hotspots?", "Choropleth (borough/CB aggregate)", 7),
        ("Q5: Geographic hotspots?", "Scatter Map (lat/lon violations)", 6),
        ("Q5: Geographic hotspots?", "Conflict Buffer Map (permit overlaps)", 5),

        # Q6: Spatial clustering? → DBSCAN, Moran's I, HexBin, Force Network
        ("Q6: Spatial clustering?", "DBSCAN Cluster Map (spatial groups)", 9),
        ("Q6: Spatial clustering?", "Moran's I Scatter (spatial autocorrelation)", 7),
        ("Q6: Spatial clustering?", "Hex-Bin Map (spatial density)", 6),
        ("Q6: Spatial clustering?", "Force Network (proximity/relationships)", 4),

        # Q7: Neighborhood rankings? → Bar, Choropleth, Treemap, Lollipop
        ("Q7: Neighborhood rankings?", "Bar Chart (side-by-side)", 9),
        ("Q7: Neighborhood rankings?", "Lollipop Chart (ordered comparison)", 8),
        ("Q7: Neighborhood rankings?", "Choropleth (borough/CB aggregate)", 7),
        ("Q7: Neighborhood rankings?", "Treemap (hierarchical ranking)", 6),

        # Q8: Spatial autocorrelation? → Moran's I, Force Network
        ("Q8: Spatial autocorrelation?", "Moran's I Scatter (spatial autocorrelation)", 9),
        ("Q8: Spatial autocorrelation?", "Hex-Bin Map (spatial density)", 5),

        # Q9: Owner compliance rates? → Bar, Stacked Bar, Dot Plot, KPI
        ("Q9: Owner compliance rates?", "Bar Chart (side-by-side)", 8),
        ("Q9: Owner compliance rates?", "Diverging Stacked Bar (positive/negative)", 7),
        ("Q9: Owner compliance rates?", "Dot Plot (precise comparison)", 6),
        ("Q9: Owner compliance rates?", "KPI Card (single metric)", 5),

        # Q10: Repeat offenders? → Bar, Scatter, Bubble, Outlier Scatter
        ("Q10: Repeat offenders?", "Outlier Scatter (flagged points)", 8),
        ("Q10: Repeat offenders?", "Scatter Plot (2D relationship)", 7),
        ("Q10: Repeat offenders?", "Bar Chart (side-by-side)", 6),
        ("Q10: Repeat offenders?", "Bubble Chart (3D scatter)", 5),

        # Q11: Owner type comparison? → Grouped Bar, Box Plot, Violin, Radar
        ("Q11: Owner type comparison?", "Grouped Bar (multi-dimensional)", 9),
        ("Q11: Owner type comparison?", "Box Plot (distribution comparison)", 8),
        ("Q11: Owner type comparison?", "Violin Plot (distribution by group)", 7),
        ("Q11: Owner type comparison?", "Radar Chart (multi-metric profile)", 6),

        # Q12: Property value predicts speed? → Scatter, Bubble, Contour, Correlation
        ("Q12: Property value predicts speed?", "Scatter Plot (2D relationship)", 9),
        ("Q12: Property value predicts speed?", "Bubble Chart (3D scatter)", 8),
        ("Q12: Property value predicts speed?", "Hexbin Plot (density scatter)", 6),
        ("Q12: Property value predicts speed?", "Correlation Heatmap (matrix)", 5),

        # Q13: Violation type distribution? → Bar, Histogram, Pie, Donut, Stacked
        ("Q13: Violation type distribution?", "Bar Chart (side-by-side)", 9),
        ("Q13: Violation type distribution?", "Stacked Bar (composition)", 7),
        ("Q13: Violation type distribution?", "Pie Chart (simple composition)", 5),
        ("Q13: Violation type distribution?", "Histogram (distribution shape)", 4),

        # Q14: Severity ranking? → Bar, Lollipop, Treemap, Bump
        ("Q14: Severity ranking?", "Lollipop Chart (ordered comparison)", 9),
        ("Q14: Severity ranking?", "Bar Chart (side-by-side)", 8),
        ("Q14: Severity ranking?", "Treemap (hierarchical ranking)", 6),
        ("Q14: Severity ranking?", "Bump Chart (ranking changes)", 4),

        # Q15: Type-specific timelines? → Ridge, Box, Violin, Grouped Bar
        ("Q15: Type-specific timelines?", "Ridge Plot (KDE by time period)", 8),
        ("Q15: Type-specific timelines?", "Box Plot (distribution comparison)", 8),
        ("Q15: Type-specific timelines?", "Violin Plot (distribution by group)", 7),
        ("Q15: Type-specific timelines?", "Grouped Bar (multi-dimensional)", 6),

        # Q16: Cost distribution? → Histogram, Box, Violin, Bubble
        ("Q16: Cost distribution?", "Histogram (distribution shape)", 8),
        ("Q16: Cost distribution?", "Box Plot (distribution comparison)", 7),
        ("Q16: Cost distribution?", "Violin Plot (distribution by group)", 6),
        ("Q16: Cost distribution?", "Bubble Chart (3D scatter)", 5),

        # Q17: Overall compliance rate? → KPI, Gauge, Metric Sparkline, Scorecard
        ("Q17: Overall compliance rate?", "KPI Card (single metric)", 10),
        ("Q17: Overall compliance rate?", "Gauge Chart (target tracking)", 8),
        ("Q17: Overall compliance rate?", "Metric Sparkline (mini trend)", 5),

        # Q18: City vs owner repairs? → Stacked Bar, Grouped Bar, Sankey, Funnel
        ("Q18: City vs owner repairs?", "100% Stacked Bar (proportions)", 9),
        ("Q18: City vs owner repairs?", "Stacked Bar (composition)", 8),
        ("Q18: City vs owner repairs?", "Sankey Diagram (flow/transitions)", 7),
        ("Q18: City vs owner repairs?", "Grouped Bar (multi-dimensional)", 6),

        # Q19: Cure window adherence? → Line, Area, Control Chart, Gauge
        ("Q19: Cure window adherence?", "Control Chart (SPC limits)", 8),
        ("Q19: Cure window adherence?", "Line Chart (trend)", 7),
        ("Q19: Cure window adherence?", "Gauge Chart (target tracking)", 7),

        # Q20: Contractor performance? → Bar, Scatter, Box, Radar
        ("Q20: Contractor performance?", "Bar Chart (side-by-side)", 8),
        ("Q20: Contractor performance?", "Scatter Plot (2D relationship)", 7),
        ("Q20: Contractor performance?", "Radar Chart (multi-metric profile)", 6),
        ("Q20: Contractor performance?", "Box Plot (distribution comparison)", 5),

        # Q21: 311→Inspection gap? → Scatter, Bubble, Funnel, Sankey
        ("Q21: 311→Inspection gap?", "Funnel Chart (drop-off analysis)", 9),
        ("Q21: 311→Inspection gap?", "Sankey Diagram (flow/transitions)", 8),
        ("Q21: 311→Inspection gap?", "Scatter Plot (2D relationship)", 6),

        # Q22: Data completeness? → Heatmap, Scorecard, Bar
        ("Q22: Data completeness?", "Scorecard (quality metrics)", 9),
        ("Q22: Data completeness?", "Heatmap (block-level density)", 7),
        ("Q22: Data completeness?", "Bar Chart (side-by-side)", 5),

        # Q23: Missing inspections? → Scatter Map, Choropleth, Scatter Plot
        ("Q23: Missing inspections?", "Scatter Map (lat/lon violations)", 9),
        ("Q23: Missing inspections?", "Choropleth (borough/CB aggregate)", 8),
        ("Q23: Missing inspections?", "Heatmap (block-level density)", 7),

        # Q24: Coverage equity? → Choropleth, Heatmap, Box, Violin
        ("Q24: Coverage equity?", "Choropleth (borough/CB aggregate)", 8),
        ("Q24: Coverage equity?", "Box Plot (distribution comparison)", 7),
        ("Q24: Coverage equity?", "Violin Plot (distribution by group)", 6),

        # Q25: Vision Zero overlap? → Scatter Map, Heatmap, Conflict Buffer
        ("Q25: Vision Zero overlap?", "Conflict Buffer Map (permit overlaps)", 9),
        ("Q25: Vision Zero overlap?", "Scatter Map (lat/lon violations)", 8),
        ("Q25: Vision Zero overlap?", "Heatmap (block-level density)", 7),

        # Q26: High-traffic areas? → Scatter Map, Heatmap, Bubble, Choropleth
        ("Q26: High-traffic areas?", "Heatmap (block-level density)", 9),
        ("Q26: High-traffic areas?", "Bubble Chart (3D scatter)", 8),
        ("Q26: High-traffic areas?", "Scatter Map (lat/lon violations)", 7),

        # Q27: Financial impact rank? → Bar, Lollipop, Treemap, Bubble
        ("Q27: Financial impact rank?", "Lollipop Chart (ordered comparison)", 9),
        ("Q27: Financial impact rank?", "Bar Chart (side-by-side)", 8),
        ("Q27: Financial impact rank?", "Treemap (hierarchical ranking)", 7),
        ("Q27: Financial impact rank?", "Bubble Chart (3D scatter)", 6),

        # Q28: Complaint volume hotspots? → Scatter Map, Heatmap, Hex-Bin
        ("Q28: Complaint volume hotspots?", "Heatmap (block-level density)", 9),
        ("Q28: Complaint volume hotspots?", "Hex-Bin Map (spatial density)", 8),
        ("Q28: Complaint volume hotspots?", "Scatter Map (lat/lon violations)", 7),

        # Q29: Future violation risk? → Scatter, Bubble, Calibration, ROC
        ("Q29: Future violation risk?", "Scatter Plot (2D relationship)", 8),
        ("Q29: Future violation risk?", "Bubble Chart (3D scatter)", 7),
        ("Q29: Future violation risk?", "Calibration Plot (prediction accuracy)", 5),

        # Q30: Repair timeline prediction? → Line, Scatter, Box, Histogram
        ("Q30: Repair timeline prediction?", "Scatter Plot (2D relationship)", 8),
        ("Q30: Repair timeline prediction?", "Line Chart (trend)", 7),
        ("Q30: Repair timeline prediction?", "Box Plot (distribution comparison)", 6),

        # Q31: Non-compliance prediction? → ROC, Calibration, Lift, Scatter
        ("Q31: Non-compliance prediction?", "ROC Curve (classifier performance)", 7),
        ("Q31: Non-compliance prediction?", "Lift Chart (model lift)", 6),
        ("Q31: Non-compliance prediction?", "Scatter Plot (2D relationship)", 5),

        # Q32: Borough benchmarking? → Grouped Bar, Radar, Parallel Coords, Dot
        ("Q32: Borough benchmarking?", "Grouped Bar (multi-dimensional)", 9),
        ("Q32: Borough benchmarking?", "Radar Chart (multi-metric profile)", 8),
        ("Q32: Borough benchmarking?", "Parallel Coordinates (multivariate)", 6),
        ("Q32: Borough benchmarking?", "Dot Plot (precise comparison)", 5),

        # Q33: Community Board ranking? → Bar, Choropleth, Treemap, Lollipop
        ("Q33: Community Board ranking?", "Choropleth (borough/CB aggregate)", 9),
        ("Q33: Community Board ranking?", "Bar Chart (side-by-side)", 8),
        ("Q33: Community Board ranking?", "Lollipop Chart (ordered comparison)", 7),
        ("Q33: Community Board ranking?", "Treemap (hierarchical ranking)", 6),

        # Q34: Multi-dimensional comparison? → Parallel Coords, SPLOM, Radar, Clustermap
        ("Q34: Multi-dimensional comparison?", "Parallel Coordinates (multivariate)", 9),
        ("Q34: Multi-dimensional comparison?", "SPLOM (scatter plot matrix)", 8),
        ("Q34: Multi-dimensional comparison?", "Radar Chart (multi-metric profile)", 7),
        ("Q34: Multi-dimensional comparison?", "Clustermap (heatmap + dendro)", 6),

        # Q35: Outlier violations? → Outlier Scatter, Isolation Forest, Strip, Scatter
        ("Q35: Outlier violations?", "Outlier Scatter (flagged points)", 10),
        ("Q35: Outlier violations?", "Isolation Forest Scatter (anomalies)", 9),
        ("Q35: Outlier violations?", "Z-Score Strip (standardized outliers)", 8),
        ("Q35: Outlier violations?", "Scatter Plot (2D relationship)", 6),

        # Q36: Unusual patterns? → Line, Parallel Coords, Heatmap, Clustermap
        ("Q36: Unusual patterns?", "Line Chart (trend)", 7),
        ("Q36: Unusual patterns?", "Clustermap (heatmap + dendro)", 8),
        ("Q36: Unusual patterns?", "Heatmap (block-level density)", 6),

        # Q37: Extreme properties? → Bubble, Scatter, Outlier Scatter, Box
        ("Q37: Extreme properties?", "Outlier Scatter (flagged points)", 9),
        ("Q37: Extreme properties?", "Bubble Chart (3D scatter)", 8),
        ("Q37: Extreme properties?", "Scatter Plot (2D relationship)", 7),
        ("Q37: Extreme properties?", "Box Plot (distribution comparison)", 5),

        # Data Patterns → Questions (first layer)
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
            text="Research Questions → Chart Recommendations Sankey<br><sub>Data Patterns → Analyst Intent → Recommended Visualizations</sub>",
            font=dict(size=16),
        ),
        font=dict(size=11),
        height=1200,
        width=1600,
        margin=dict(l=20, r=20, t=80, b=20),
    )

    return fig


if __name__ == "__main__":
    fig = generate_research_questions_sankey()
    fig.show()
    # Save to HTML
    fig.write_html("research_questions_sankey.html")
    print("Sankey saved to research_questions_sankey.html")
