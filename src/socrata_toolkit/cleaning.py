from __future__ import annotations

import re

import numpy as np
import pandas as pd


def standardize_boroughs(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Normalize NYC borough names to standard uppercase."""
    mapping = {
        "1": "MANHATTAN",
        "MN": "MANHATTAN",
        "NEW YORK": "MANHATTAN",
        "2": "BRONX",
        "BX": "BRONX",
        "3": "BROOKLYN",
        "BK": "BROOKLYN",
        "KINGS": "BROOKLYN",
        "4": "QUEENS",
        "QN": "QUEENS",
        "5": "STATEN ISLAND",
        "SI": "STATEN ISLAND",
        "RICHMOND": "STATEN ISLAND",
    }
    out = df.copy()
    if col in out.columns:
        out[col] = out[col].astype(str).str.upper().str.strip()
        out[col] = out[col].replace(mapping)
        # Final pass for standard names
        valid = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
        out.loc[~out[col].isin(valid), col] = "UNKNOWN"
    return out


def standardize_postcodes(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ensure postcodes are 5-digit strings."""
    out = df.copy()
    if col in out.columns:
        out[col] = out[col].astype(str).str.extract(r"(\d{5})")[0].fillna("")
    return out


def standardize_bbl(
    df: pd.DataFrame, boro_col: str, block_col: str, lot_col: str, target_col: str = "bbl"
) -> pd.DataFrame:
    """Create a 10-digit BBL (Borough-Block-Lot) string."""
    out = df.copy()
    boro_map = {
        "MANHATTAN": "1",
        "BRONX": "2",
        "BROOKLYN": "3",
        "QUEENS": "4",
        "STATEN ISLAND": "5",
    }

    def format_bbl(row):
        try:
            b = boro_map.get(str(row[boro_col]).upper(), "0")
            block = str(int(float(row[block_col]))).zfill(5)
            lot = str(int(float(row[lot_col]))).zfill(4)
            return f"{b}{block}{lot}"
        except:
            return None

    if all(c in out.columns for c in [boro_col, block_col, lot_col]):
        out[target_col] = out.apply(format_bbl, axis=1)
    return out


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Snake_case column names and remove special characters."""
    out = df.copy()
    out.columns = [
        re.sub(r"[^a-z0-9_]", "", c.lower().replace(" ", "_").replace("-", "_"))
        for c in out.columns
    ]
    return out


def infer_and_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert object columns to numeric or datetime."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            # Try numeric
            try:
                out[col] = pd.to_numeric(out[col])
                continue
            except:
                pass

            # Try datetime
            try:
                if "date" in col.lower() or "time" in col.lower() or "timestamp" in col.lower():
                    out[col] = pd.to_datetime(out[col])
            except:
                pass
    return out


def remove_outliers(df: pd.DataFrame, col: str, z_threshold: float = 3) -> pd.DataFrame:
    """Remove rows where column value is more than N standard deviations from mean."""
    out = df.copy()
    if col in out.columns and pd.api.types.is_numeric_dtype(out[col]):
        z_scores = (out[col] - out[col].mean()) / out[col].std()
        out = out[np.abs(z_scores) < z_threshold]
    return out
