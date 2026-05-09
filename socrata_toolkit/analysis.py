from types import SimpleNamespace
import pandas as pd


def profile_dataframe(df: pd.DataFrame):
    """
    Produce a simple profile of the dataframe used by the test suite.
    """
    profile = {}

    profile["row_count"] = len(df)
    profile["column_count"] = df.shape[1]

    # REQUIRED BY TEST SUITE
    profile["null_counts"] = df.isna().sum().to_dict()

    # Column-level stats
    profile["columns"] = {
        col: {
            "dtype": str(df[col].dtype),
            "missing": int(df[col].isna().sum()),
            "unique": int(df[col].nunique(dropna=True)),
        }
        for col in df.columns
    }

    return SimpleNamespace(**profile)


def _count_duplicate_rows(df: pd.DataFrame, key_columns):
    """
    Count duplicate rows, excluding rows that are duplicates
    only because the key columns repeat.
    """
    full_dupes = df.duplicated(keep="first")
    key_dupes = df.duplicated(subset=key_columns, keep="first")
    return int((full_dupes & ~key_dupes).sum())


def quality_report(df: pd.DataFrame, key_columns):
    """
    Produce a simple quality report used by the test suite.
    """
    report = {}

    report["row_count"] = len(df)

    report["missing_values"] = df.isna().sum().to_dict()

    report["duplicate_rows"] = _count_duplicate_rows(df, key_columns)

    # dict: each key column → duplicate count
    report["duplicate_keys"] = {
        col: int(df.duplicated(subset=[col]).sum())
        for col in key_columns
    }

    return report
