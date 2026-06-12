"""
Standardized units mapping for NYC DOT visualizations.

Provides centralized unit specifications for all metrics used in charts,
ensuring consistency across all visualizations.

Usage:
    from socrata_toolkit.viz.units import UNITS, get_unit_label, apply_units

    # Get the unit label for a metric
    label = get_unit_label('violation_count')  # "Number of Violations (count)"

    # Build chart axes with units
    fig.update_layout(yaxis_title=get_unit_label('violation_count'))
"""

# Comprehensive units mapping for NYC DOT datasets
UNITS = {
    # Violation metrics
    'violation_count': 'Number of Violations (count)',
    'violations': 'Number of Violations (count)',
    'total_violations': 'Total Violations (count)',
    'open_violations': 'Open Violations (count)',
    'closed_violations': 'Closed Violations (count)',

    # Inspection metrics
    'inspection_count': 'Number of Inspections (count)',
    'inspections': 'Number of Inspections (count)',
    'total_inspections': 'Total Inspections (count)',

    # Completion/Progress metrics
    'completion_rate': 'Completion Rate (%)',
    'completion_pct': 'Completion Rate (%)',
    'completed': 'Completed (count)',
    'completed_ramps': 'Completed Ramps (count)',
    'total_ramps': 'Total Ramps (count)',
    'ramp_progress': 'Ramp Progress (count)',

    # Cost metrics
    'cost': 'Cost (USD)',
    'total_cost': 'Total Cost (USD)',
    'average_cost': 'Average Cost (USD)',
    'cost_per_violation': 'Cost per Violation (USD)',
    'budget': 'Budget (USD)',
    '20_year_cost': '20-Year Total Cost (USD)',

    # Quality/Score metrics
    'quality_score': 'Quality Score (0-100)',
    'condition_score': 'Condition Score (0-100)',
    'score': 'Quality Score (0-100)',
    'confidence_level': 'Confidence Level (%)',
    'accuracy': 'Classification Accuracy (%)',
    'null_pct': 'Null Rate (%)',
    'completeness': 'Completeness (%)',

    # Time metrics
    'days_elapsed': 'Days Elapsed (days)',
    'days_to_completion': 'Days to Completion (days)',
    'time_to_completion': 'Time to Completion (days)',
    'inspection_date': 'Inspection Date (YYYY-MM-DD)',
    'created_date': 'Created Date (YYYY-MM-DD)',
    'completion_date': 'Completion Date (YYYY-MM-DD)',
    'month': 'Month (YYYY-MM)',
    'year': 'Year (YYYY)',
    'week': 'Week Number',
    'lifespan': 'Median Lifespan (years)',
    'survival_time': 'Survival Time (months)',
    'elapsed_time': 'Elapsed Time (months)',

    # Spatial metrics
    'latitude': 'Latitude (degrees)',
    'longitude': 'Longitude (degrees)',
    'lat': 'Latitude (degrees)',
    'lon': 'Longitude (degrees)',
    'distance': 'Distance (meters)',
    'distance_meters': 'Distance (meters)',
    'buffer_distance': 'Buffer Distance (meters)',
    'density': 'Density (count/km²)',
    'violation_density': 'Violation Density (count/km²)',

    # Statistical metrics
    'p_value': 'P-value (0-1)',
    'effect_size': 'Effect Size (Cohen\'s d)',
    'correlation': 'Correlation (−1 to 1)',
    'mean_silhouette': 'Mean Silhouette Coefficient (−1 to 1)',
    'inertia': 'Inertia (sum of squared distances)',
    'davies_bouldin': 'Davies-Bouldin Index (lower is better)',
    'calinski_harabasz': 'Calinski-Harabasz Index (higher is better)',
    'confidence_interval': '95% Confidence Interval (±%)',
    'ci_lower': '95% CI Lower Bound (%)',
    'ci_upper': '95% CI Upper Bound (%)',

    # Performance metrics
    'latency': 'Response Time (ms)',
    'throughput': 'Throughput (rows/sec)',
    'cache_hit_rate': 'Cache Hit Rate (%)',
    'uptime': 'Uptime (%)',
    'error_rate': 'Error Rate (%)',

    # Count-based metrics (generic)
    'count': 'Count',
    'total': 'Total (count)',
    'sample_size': 'Sample Size (n)',
    'n': 'Sample Size (n)',

    # ID/Key fields (no units)
    'id': 'ID',
    'block_id': 'Block ID',
    'inspection_id': 'Inspection ID',
    'violation_id': 'Violation ID',
    'permit_id': 'Permit ID',
    'objectid': 'Object ID',
    'borough': 'Borough',
    'status': 'Status',
    'category': 'Category',
    'type': 'Type',
    'name': 'Name',
    'inspector': 'Inspector Name',
    'contractor': 'Contractor Name',
}

def get_unit_label(column_name: str, default: str = '') -> str:
    """
    Get the standardized unit label for a column.

    Args:
        column_name: Name of the column (case-insensitive)
        default: Default label if column not found

    Returns:
        Standardized label with units (e.g., "Number of Violations (count)")

    Examples:
        >>> get_unit_label('violation_count')
        'Number of Violations (count)'

        >>> get_unit_label('cost')
        'Cost (USD)'

        >>> get_unit_label('unknown_column', 'Unknown Metric')
        'Unknown Metric'
    """
    normalized = column_name.lower().strip()
    return UNITS.get(normalized, default or column_name.replace('_', ' ').title())

def apply_units_to_axes(fig, x_col: str = None, y_col: str = None, z_col: str = None):
    """
    Apply standardized units to chart axes.

    Args:
        fig: Plotly Figure object
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        z_col: Column name for color/z-axis

    Returns:
        Modified figure with units applied

    Example:
        >>> from socrata_toolkit.viz.plotly import borough_bar_chart
        >>> fig = borough_bar_chart(df, value_col='violations')
        >>> apply_units_to_axes(fig, y_col='violations')
    """
    updates = {}

    if x_col:
        updates['xaxis_title'] = get_unit_label(x_col)

    if y_col:
        updates['yaxis_title'] = get_unit_label(y_col)

    if z_col:
        updates['coloraxis_colorbar'] = dict(title=get_unit_label(z_col))

    if updates:
        fig.update_layout(**updates)

    return fig

# Common axis pairs for quick reference
AXIS_PAIRS = {
    'borough_violations': {
        'x': 'borough',
        'y': 'violation_count',
    },
    'time_series_violations': {
        'x': 'month',
        'y': 'violation_count',
    },
    'material_lifespan': {
        'x': 'lifespan',
        'y': '20_year_cost',
    },
    'geographic': {
        'x': 'longitude',
        'y': 'latitude',
        'z': 'condition_score',
    },
}
