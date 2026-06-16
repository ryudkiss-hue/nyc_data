# NYC DOT Data Dictionary with Units

**Purpose:** Standardized reference for all columns across NYC Open Data datasets used in SIM Workflows.

**Format:** Every column specifies its unit of measurement explicitly.

---

## Core Violation Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `objectid` | Integer | N/A (ID) | Unique identifier for each violation record in Socrata |
| `violation_count` | Integer | count | Total number of violations associated with this record |
| `condition_score` | Float | 0-100 | Numeric assessment of sidewalk condition (0=poor, 100=excellent) |
| `inspection_date` | DateTime | YYYY-MM-DD | Date when the sidewalk was formally inspected |
| `borough` | String | N/A (Category) | NYC borough name (Manhattan, Bronx, Brooklyn, Queens, Staten Island) |

## Ramp Progress Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `ramp_id` | String | N/A (ID) | Unique identifier for each accessibility ramp |
| `completed_ramps` | Integer | count | Number of ramps with construction completed |
| `total_ramps` | Integer | count | Total number of ramps in the accessibility program |
| `completion_rate` | Float | % (percent) | Percentage of ramps that have been completed (0-100%) |
| `completion_date` | DateTime | YYYY-MM-DD | Expected or actual date ramp construction will be finished |

## Cost & Budget Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `cost` | Decimal | USD (dollars) | Total cost for repair or construction work performed |
| `total_cost` | Decimal | USD (dollars) | Cumulative cost across all violations in a period |
| `average_cost` | Decimal | USD (dollars) | Mean cost per violation for the specified period |
| `budget` | Decimal | USD (dollars) | Allocated budget for sidewalk repair program |
| `cost_per_violation` | Decimal | USD (dollars) | Cost normalized by violation count |

## Time & Duration Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `days_elapsed` | Integer | days | Number of calendar days since violation was reported |
| `days_to_completion` | Integer | days | Estimated or actual days required to complete repairs |
| `lifespan` | Float | years | Expected median lifespan of repair or material |
| `month` | DateTime | YYYY-MM | Year and month for time-series analysis (monthly granularity) |
| `year` | Integer | YYYY | Calendar year for annual aggregations |

## Geographic & Spatial Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `latitude` | Float | degrees | Geographic latitude coordinate (WGS84, −90 to 90) |
| `longitude` | Float | degrees | Geographic longitude coordinate (WGS84, −180 to 180) |
| `distance` | Float | meters | Distance from location to reference point (e.g., intersection) |
| `density` | Float | count/km² | Count of violations per square kilometer |
| `buffer_distance` | Float | meters | Spatial buffer radius for conflict detection analysis |

## Quality & Scoring Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `quality_score` | Float | 0-100 | Overall data quality rating for the dataset |
| `condition_score` | Float | 0-100 | Sidewalk condition assessment (0=poor, 100=excellent) |
| `accuracy` | Float | % (percent) | Percentage of classifications or predictions that are correct |
| `completeness` | Float | % (percent) | Percentage of non-null values in the dataset |
| `null_pct` | Float | % (percent) | Percentage of missing or null values |

## Statistical & Performance Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `p_value` | Float | 0-1 (unitless) | Statistical significance indicator (lower = more significant) |
| `effect_size` | Float | Cohen's d | Magnitude of difference between groups (effect magnitude) |
| `correlation` | Float | −1 to 1 (unitless) | Pearson correlation coefficient between two variables |
| `mean_silhouette` | Float | −1 to 1 (unitless) | Clustering quality metric (higher = better separation) |
| `inertia` | Float | sum of squared distances | K-means objective function value (lower = tighter clusters) |

## Sample Size & Counts Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `sample_size` | Integer | n (count) | Number of observations or records in the sample |
| `total` | Integer | count | Total count of items in the specified category |
| `count` | Integer | count | Frequency or occurrence count for a metric |
| `inspection_count` | Integer | count | Total number of inspections performed |
| `completed` | Integer | count | Number of completed items (repairs, ramps, etc.) |

## Categorical & Identifier Dataset

| Column Title | Data Type | Unit of Measurement | Description |
|---|---|---|---|
| `block_id` | String | N/A (ID) | Unique identifier for a city block from NYC PLUTO dataset |
| `status` | String | N/A (Category) | Current state of a violation or repair (Open, Closed, In Progress) |
| `category` | String | N/A (Category) | Classification of violation type (e.g., "Pothole", "Crack") |
| `inspector` | String | N/A (Name) | Name of the inspector who conducted the assessment |
| `contractor` | String | N/A (Name) | Name of the contractor performing repairs |

---

## IMPORTANT: Units Always Present

Every visualization across the platform now includes explicit units:

✅ **Charts must include units in:**
- X-axis title: e.g., "Violation Count (count)" NOT just "Violations"
- Y-axis title: e.g., "Days to Completion (days)" NOT just "Days"
- Color bar title: e.g., "Quality Score (0-100)" NOT just "Score"
- Legend entries: e.g., "Open Violations (count)" NOT just "Open"
- Hover tooltips: e.g., "Cost: $1,250 (USD)" NOT just "$1,250"

✅ **Examples of CORRECT labeling:**
- "Violation Count by Borough (2026-Q2)" — metric + dimension + time
- Y-axis: "Number of Violations (count)"
- X-axis: "Borough Name"

❌ **Examples of INCORRECT labeling (avoid):**
- "Violations" — no unit
- "Count" — too generic
- "2026-Q2" in title — time belongs in subtitle or legend
- "Days" — should specify what the days measure

---

## Usage in Code

```python
from socrata_toolkit.viz.units import get_unit_label, apply_units_to_axes

# Get unit label for a column
violation_label = get_unit_label('violation_count')
# Returns: "Number of Violations (count)"

# Apply units to all axes automatically
fig = apply_units_to_axes(fig, x_col='borough', y_col='violation_count')

# Custom mapping for special cases
custom_title = f"{get_unit_label('violation_count')} by {get_unit_label('borough')}"
fig.update_layout(title=custom_title)
```

---

## Standards Applied Since 2026-06-11

All visualizations created or updated after **2026-06-11** must follow this standard:

1. ✅ Every axis must have a label with units
2. ✅ Every title must include metric + dimension + time period
3. ✅ Every legend must specify what each series represents + unit
4. ✅ Every color scale must have a unit label
5. ✅ Every hover tooltip must show the unit

**Non-compliance is a bug.** Report missing units as issues.

---

**Last Updated:** 2026-06-11  
**Maintained By:** NYC DOT SIM Workflows  
**Version:** 1.0
