# `socrata_toolkit.cleaning` — Data Normalization

**File:** `socrata_toolkit/cleaning.py` | **Pillar:** Cleaning  
**Dependencies:** `pandas`, `numpy`

Utility functions for standardizing and cleaning NYC municipal datasets. All functions are pure — they return new DataFrames without modifying the input.

---

## `standardize_boroughs(df, col) → pd.DataFrame`
Normalize NYC borough names to standard uppercase. Handles numeric codes, abbreviations, and legacy names.

**Mapping:**

| Input | Normalized |
|-------|-----------|
| `"1"`, `"MN"`, `"NEW YORK"` | `MANHATTAN` |
| `"2"`, `"BX"` | `BRONX` |
| `"3"`, `"BK"`, `"KINGS"` | `BROOKLYN` |
| `"4"`, `"QN"` | `QUEENS` |
| `"5"`, `"SI"`, `"RICHMOND"` | `STATEN ISLAND` |
| Any unrecognized value | `UNKNOWN` |

```python
from socrata_toolkit.cleaning import standardize_boroughs

df = standardize_boroughs(df, col="borough")
# "BK" → "BROOKLYN", "New York" → "MANHATTAN", "Unknown Value" → "UNKNOWN"
```

---

## `standardize_postcodes(df, col) → pd.DataFrame`
Extract and normalize 5-digit ZIP codes. Invalid/missing values become empty strings.

```python
from socrata_toolkit.cleaning import standardize_postcodes

df = standardize_postcodes(df, col="zip_code")
# "10001-1234" → "10001", "ABCDE" → ""
```

---

## `standardize_bbl(df, boro_col, block_col, lot_col, target_col="bbl") → pd.DataFrame`
Create a standard 10-digit NYC BBL (Borough-Block-Lot) identifier string.

**Format:** `{boro_digit}{block:05d}{lot:04d}`

| Component | Width | Example |
|-----------|-------|---------|
| Borough digit | 1 | `3` (Brooklyn) |
| Block | 5 (zero-padded) | `00123` |
| Lot | 4 (zero-padded) | `0045` |
| **Full BBL** | **10** | **`3001230045`** |

```python
from socrata_toolkit.cleaning import standardize_bbl

df = standardize_bbl(df, boro_col="borough", block_col="block",
                     lot_col="lot", target_col="bbl")
print(df["bbl"].head())  # "3001230045", "1000010001", ...
```

---

## `clean_column_names(df) → pd.DataFrame`
Standardize column names to `snake_case`:
- Lowercase
- Spaces and hyphens → underscores
- Remove all non-alphanumeric/underscore characters

```python
from socrata_toolkit.cleaning import clean_column_names

df = clean_column_names(df)
# "Street Address" → "street_address"
# "Zip-Code" → "zip_code"
# "311 Complaint #" → "311_complaint_"
```

---

## `infer_and_convert_types(df) → pd.DataFrame`
Auto-convert `object` dtype columns to numeric or datetime where possible.

**Logic:**
1. Try `pd.to_numeric()` — if it succeeds, convert
2. If column name contains `date`, `time`, or `timestamp`, try `pd.to_datetime()`
3. Otherwise, leave as `object`

```python
from socrata_toolkit.cleaning import infer_and_convert_types

df = infer_and_convert_types(df)
# "violations" (was "object") → int64
# "created_date" → datetime64
```

---

## `remove_outliers(df, col, z_threshold=3) → pd.DataFrame`
Remove rows where the specified column value is more than `z_threshold` standard deviations from the mean.

```python
from socrata_toolkit.cleaning import remove_outliers

# Remove extreme violations counts (> 3σ from mean)
df_clean = remove_outliers(df, col="violations", z_threshold=3)
print(f"Removed {len(df) - len(df_clean)} outlier rows")
```

- Only applies to numeric columns (checked via `pd.api.types.is_numeric_dtype`)
- Non-numeric columns pass through unchanged

---

## Recommended Cleaning Pipeline

```python
from socrata_toolkit.cleaning import (
    clean_column_names,
    standardize_boroughs,
    standardize_postcodes,
    standardize_bbl,
    infer_and_convert_types,
    remove_outliers
)

def clean_nyc_dataset(df, borough_col="borough", zip_col="postcode",
                      boro_col=None, block_col=None, lot_col=None):
    df = clean_column_names(df)
    if borough_col in df.columns:
        df = standardize_boroughs(df, col=borough_col)
    if zip_col in df.columns:
        df = standardize_postcodes(df, col=zip_col)
    if all(c in df.columns for c in [boro_col, block_col, lot_col] if c):
        df = standardize_bbl(df, boro_col=boro_col,
                             block_col=block_col, lot_col=lot_col)
    df = infer_and_convert_types(df)
    return df
```
