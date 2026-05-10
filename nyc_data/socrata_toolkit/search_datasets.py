"""
Advanced Socrata Dataset Search UI
----------------------------------
Supports:

1. Simple keyword search
2. Advanced SoQL-powered catalog search
3. Metadata filtering
4. Sorting
5. Domain restriction
6. Dataset type filtering
7. Pagination
8. Raw JSON inspection
"""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from socrata_toolkit.client import SocrataClient


# ---------------------------------------------------
# Setup
# ---------------------------------------------------

st.set_page_config(
    page_title="Socrata Dataset Search",
    layout="wide",
)

client = SocrataClient()


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def clean_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make returned catalog data easier to read.
    """
    cols = []

    preferred = [
        "id",
        "name",
        "description",
        "domain",
        "category",
        "type",
        "updatedAt",
        "rowsUpdatedAt",
        "downloads",
        "provenance",
    ]

    for col in preferred:
        if col in df.columns:
            cols.append(col)

    remainder = [c for c in df.columns if c not in cols]

    return df[cols + remainder]


def build_catalog_filters(
    domain: str | None,
    category: str | None,
    dataset_type: str | None,
    only_public: bool,
) -> str:
    """
    Build Socrata catalog filter expression.
    """

    clauses = []

    if domain:
        clauses.append(f'domain="{domain}"')

    if category:
        clauses.append(f'category="{category}"')

    if dataset_type:
        clauses.append(f'type="{dataset_type}"')

    if only_public:
        clauses.append('publication_stage="published"')

    if not clauses:
        return ""

    return " AND ".join(clauses)


# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------

st.sidebar.title("Search Options")

mode = st.sidebar.radio(
    "Mode",
    [
        "Regular",
        "Advanced",
    ],
)

limit = st.sidebar.slider(
    "Limit",
    min_value=10,
    max_value=500,
    value=50,
    step=10,
)

offset = st.sidebar.number_input(
    "Offset",
    min_value=0,
    value=0,
)

show_raw = st.sidebar.checkbox("Show raw JSON")


# ---------------------------------------------------
# Regular Search
# ---------------------------------------------------

if mode == "Regular":
    st.title("Dataset Search")

    query = st.text_input(
        "Keyword search",
        placeholder="sidewalk contracts",
    )

    if query:
        with st.spinner("Searching..."):
            results = client.search_datasets(
                query=query,
                limit=limit,
                offset=offset,
            )

        if len(results) == 0:
            st.warning("No datasets found.")
        else:
            st.success(f"{len(results)} datasets found")
            st.dataframe(
                clean_results(results),
                use_container_width=True,
            )

            if show_raw:
                st.json(results.to_dict("records"))


# ---------------------------------------------------
# Advanced Search
# ---------------------------------------------------

else:
    st.title("Advanced Socrata Search")

    keyword = st.text_input(
        "Keyword",
        placeholder="sidewalk",
    )

    col1, col2 = st.columns(2)

    with col1:
        domain = st.text_input(
            "Domain",
            placeholder="data.cityofnewyork.us",
        )

        category = st.text_input(
            "Category",
            placeholder="Transportation",
        )

    with col2:
        dataset_type = st.selectbox(
            "Dataset Type",
            [
                "",
                "table",
                "map",
                "chart",
                "story",
                "dataset",
            ],
        )

        sort_by = st.selectbox(
            "Sort By",
            [
                "relevance",
                "updatedAt",
                "downloads",
                "createdAt",
                "rowsUpdatedAt",
            ],
        )

    only_public = st.checkbox(
        "Published only",
        value=True,
    )

    search_button = st.button("Run Advanced Search")

    if search_button:
        filters = build_catalog_filters(
            domain=domain or None,
            category=category or None,
            dataset_type=dataset_type or None,
            only_public=only_public,
        )

        with st.spinner("Running advanced catalog query..."):

            results = client.search_catalog(
                search_context=keyword or None,
                filters=filters,
                order=sort_by,
                limit=limit,
                offset=offset,
            )

        if len(results) == 0:
            st.warning("No datasets found.")
        else:
            st.success(f"{len(results)} datasets found")

            st.dataframe(
                clean_results(results),
                use_container_width=True,
            )

            if show_raw:
                st.subheader("Raw JSON")
                st.json(
                    json.loads(
                        results.to_json(
                            orient="records"
                        )
                    )
                )


# ---------------------------------------------------
# Optional direct SoQL query panel
# ---------------------------------------------------

st.divider()
st.subheader("Direct SoQL Catalog Query")

with st.expander("Run custom SoQL"):

    raw_soql = st.text_area(
        "Custom $query",
        placeholder="""
SELECT *
WHERE category='Transportation'
ORDER BY updatedAt DESC
LIMIT 50
        """.strip(),
        height=150,
    )

    if st.button("Execute SoQL"):
        if raw_soql.strip():
            with st.spinner("Executing SoQL..."):
                df = client.catalog_query(
                    soql=raw_soql,
                )

            st.dataframe(
                df,
                use_container_width=True,
            )

            if show_raw:
                st.json(df.to_dict("records"))
