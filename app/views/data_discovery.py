"""Socrata Discovery — search and browse open datasets across NYC Open Data."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.services.nl_query import HAS_ANTHROPIC, nl_to_soql, validate_soql

_DISCOVERY_URL = "https://api.us.socrata.com/api/catalog/v1"
_DEFAULT_DOMAIN = "data.cityofnewyork.us"
_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "").strip() or None

# Known asset types supported by the Discovery API
_ASSET_TYPES = ["dataset", "map", "chart", "calendar", "href", "filter", "file", "api"]

# Broad category set used on NYC Open Data
_NYC_CATEGORIES = [
    "Business", "City Government", "Education", "Environment",
    "Health", "Housing & Development", "Public Safety", "Recreation",
    "Social Services", "Transportation",
]

# --------------------------------------------------------------------------- #
# Discovery API helpers
# --------------------------------------------------------------------------- #

def _headers() -> dict[str, str]:
    token = os.getenv("SOCRATA_APP_TOKEN", "").strip() or _APP_TOKEN
    h: dict[str, str] = {"Accept": "application/json"}
    if token:
        h["X-App-Token"] = token
    return h

@st.cache_data(ttl=300, show_spinner=False)
def _search_catalog(
    q: str,
    domains: tuple[str, ...],
    categories: tuple[str, ...],
    tags: tuple[str, ...],
    asset_types: tuple[str, ...],
    limit: int,
    offset: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if q:
        params["q"] = q
    if domains:
        params["domains"] = ",".join(domains)
    if categories:
        params["categories"] = ",".join(categories)
    if tags:
        params["tags"] = ",".join(tags)
    if asset_types:
        params["asset_types"] = ",".join(asset_types)

    try:
        r = requests.get(_DISCOVERY_URL, params=params, headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out (15 s). Try a narrower query."}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
    except Exception as exc:
        return {"error": str(exc)}

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_metadata(domain: str, fourfour: str) -> dict[str, Any]:
    url = f"https://{domain}/api/views/{fourfour}.json"
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_sample(domain: str, fourfour: str, limit: int = 25) -> pd.DataFrame:
    url = f"https://{domain}/resource/{fourfour}.json"
    try:
        r = requests.get(
            url,
            params={"$limit": limit},
            headers={**_headers(), "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as exc:
        return pd.DataFrame({"error": [str(exc)]})

def _results_to_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        res = r.get("resource", {})
        link = r.get("link", "")
        meta = r.get("metadata", {})
        rows.append({
            "name": res.get("name", ""),
            "id": res.get("id", ""),
            "domain": meta.get("domain", _DEFAULT_DOMAIN),
            "type": res.get("type", ""),
            "category": meta.get("categories", [""])[0] if meta.get("categories") else "",
            "description": (res.get("description") or "")[:120],
            "updated": res.get("updatedAt", "")[:10],
            "rows": res.get("rows_updated_at") or "",
            "link": link,
        })
    return pd.DataFrame(rows)

# --------------------------------------------------------------------------- #
# SoQL query builder helper
# --------------------------------------------------------------------------- #

def _build_soql(conditions: list[dict]) -> str:
    """Turn a list of {field, op, value} dicts into a SoQL WHERE clause."""
    parts = []
    for c in conditions:
        field = c.get("field", "").strip()
        op = c.get("op", "=")
        value = c.get("value", "").strip()
        no_value_ops = ("is_null", "is_not_null")
        if not field or (not value and op not in no_value_ops):
            continue
        if op == "=":
            parts.append(f"{field} = '{value}'")
        elif op == "!=":
            parts.append(f"{field} != '{value}'")
        elif op == "contains":
            parts.append(f"upper({field}) like upper('%{value}%')")
        elif op == "not_like":
            parts.append(f"upper({field}) not like upper('%{value}%')")
        elif op == "starts_with":
            parts.append(f"starts_with(upper({field}), upper('{value}'))")
        elif op == "not_starts_with":
            parts.append(f"NOT starts_with(upper({field}), upper('{value}'))")
        elif op == "between":
            lo, _, hi = value.partition(",")
            if lo.strip() and hi.strip():
                parts.append(f"{field} between '{lo.strip()}' and '{hi.strip()}'")
        elif op == "not_between":
            lo, _, hi = value.partition(",")
            if lo.strip() and hi.strip():
                parts.append(f"{field} not between '{lo.strip()}' and '{hi.strip()}'")
        elif op == "in":
            vals = ", ".join(f"'{v.strip()}'" for v in value.split(",") if v.strip())
            parts.append(f"{field} in({vals})")
        elif op == "not_in":
            vals = ", ".join(f"'{v.strip()}'" for v in value.split(",") if v.strip())
            parts.append(f"{field} not in({vals})")
        elif op == "is_null":
            parts.append(f"{field} IS NULL")
        elif op == "is_not_null":
            parts.append(f"{field} IS NOT NULL")
        elif op in (">", "<", ">=", "<="):
            parts.append(f"{field} {op} '{value}'")
    return " AND ".join(parts)

# --------------------------------------------------------------------------- #
# Main page renderer
# --------------------------------------------------------------------------- #

def render_data_discovery_page() -> None:
    st.subheader("🔍 Socrata Data Discovery")
    st.caption(
        "Search across NYC Open Data and all Socrata-hosted portals. "
        "Find datasets relevant to sidewalk inspection, construction coordination, "
        "ADA ramp progress, and more."
    )

    token_val = os.getenv("SOCRATA_APP_TOKEN", "").strip()
    if not token_val:
        st.warning(
            "No Socrata App Token configured. Requests may be rate-limited. "
            "Add your token in ⚙️ Settings → 🔑 API Tokens.",
            icon="⚠️",
        )

    tab_search, tab_builder, tab_preview, tab_nl = st.tabs([
        "🔎 Search & Filter",
        "🛠️ SoQL Query Builder",
        "📋 Dataset Preview",
        "🤖 NL Query",
    ])

    # ------------------------------------------------------------------ #
    # Tab 1 — Search & Filter
    # ------------------------------------------------------------------ #
    with tab_search:
        _render_search_tab()

    # ------------------------------------------------------------------ #
    # Tab 2 — SoQL Query Builder
    # ------------------------------------------------------------------ #
    with tab_builder:
        _render_soql_tab()

    # ------------------------------------------------------------------ #
    # Tab 3 — Dataset Preview
    # ------------------------------------------------------------------ #
    with tab_preview:
        _render_preview_tab()

    # ------------------------------------------------------------------ #
    # Tab 4 — NL Query
    # ------------------------------------------------------------------ #
    with tab_nl:
        _render_nl_query_tab()

def _render_search_tab() -> None:
    with st.form("discovery_search_form"):
        col1, col2 = st.columns([3, 1])
        q = col1.text_input(
            "Search query",
            placeholder="e.g. sidewalk inspection, ADA ramp, street construction",
            help="Full-text search across dataset names, descriptions, and column names.",
        )
        result_limit = col2.selectbox("Results per page", [10, 25, 50, 100], index=1)

        with st.expander("⚙️ Advanced filters", expanded=False):
            af_col1, af_col2 = st.columns(2)

            domains_raw = af_col1.text_input(
                "Domains (comma-separated)",
                value=_DEFAULT_DOMAIN,
                help="e.g. data.cityofnewyork.us, opendata.cityofnewyork.us",
            )
            domains = tuple(d.strip() for d in domains_raw.split(",") if d.strip())

            selected_cats = af_col1.multiselect(
                "Categories",
                _NYC_CATEGORIES,
                default=[],
                help="Filter by dataset category on the portal.",
            )

            selected_types = af_col2.multiselect(
                "Asset types",
                _ASSET_TYPES,
                default=["dataset"],
                help="Limit to specific Socrata asset types.",
            )

            tags_raw = af_col2.text_input(
                "Tags (comma-separated)",
                placeholder="e.g. sidewalk, permits, construction",
                help="Filter by dataset tags.",
            )
            tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())

            page_offset = st.number_input("Page offset (for pagination)", min_value=0, value=0, step=result_limit)

            regex_filter = st.text_input(
                "Client-side regex filter (on dataset name)",
                placeholder="e.g. (?i)sidewalk|ramp|curb",
                help="Applied after API results are returned. Python regex syntax.",
            )

        submitted = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)

    if submitted or st.session_state.get("_discovery_last_q") == q:
        st.session_state["_discovery_last_q"] = q
        with st.spinner("Searching Socrata catalog…"):
            data = _search_catalog(
                q=q,
                domains=domains,
                categories=tuple(selected_cats),
                tags=tags,
                asset_types=tuple(selected_types),
                limit=result_limit,
                offset=int(page_offset),
            )

        if "error" in data:
            st.error(f"Discovery API error: {data['error']}")
            return

        results = data.get("results", [])
        total = data.get("resultSetSize", len(results))

        if not results:
            st.info("No datasets found. Try broader terms or remove some filters.")
            return

        df = _results_to_df(results)

        # Apply client-side regex if provided
        if regex_filter:
            try:
                mask = df["name"].str.contains(regex_filter, regex=True, na=False)
                df = df[mask]
                st.caption(f"Regex `{regex_filter}` matched {len(df)} of {len(results)} results.")
            except re.error as exc:
                st.warning(f"Invalid regex: {exc}")

        st.success(f"Found **{total:,}** dataset(s) total — showing {len(df)} on this page.")

        # Render results
        for _, row in df.iterrows():
            with st.container():
                col_info, col_actions = st.columns([5, 1])
                with col_info:
                    st.markdown(f"**{row['name']}** `{row['id']}`")
                    meta_parts = []
                    if row["domain"]:
                        meta_parts.append(f"🌐 {row['domain']}")
                    if row["type"]:
                        meta_parts.append(f"📁 {row['type']}")
                    if row["category"]:
                        meta_parts.append(f"🏷️ {row['category']}")
                    if row["updated"]:
                        meta_parts.append(f"🗓️ {row['updated']}")
                    if meta_parts:
                        st.caption("  ·  ".join(meta_parts))
                    if row["description"]:
                        st.caption(row["description"])
                with col_actions:
                    if st.button(
                        "👁 Preview",
                        key=f"prev_{row['id']}",
                        use_container_width=True,
                        help="Preview schema and sample rows",
                    ):
                        st.session_state["_discovery_preview_id"] = row["id"]
                        st.session_state["_discovery_preview_domain"] = row["domain"]
                        st.session_state["_discovery_preview_name"] = row["name"]
                    if st.button(
                        "➕ Add",
                        key=f"add_{row['id']}",
                        use_container_width=True,
                        help="Add to session registry for use in other views",
                    ):
                        _add_to_session(row["id"], row["domain"], row["name"])
                st.divider()

        # Download full result list
        if not df.empty:
            st.download_button(
                "⬇ Export results (CSV)",
                df.drop(columns=["link"], errors="ignore").to_csv(index=False).encode("utf-8"),
                "discovery_results.csv",
                mime="text/csv",
            )

        # Show added datasets
        if st.session_state.get("_discovery_added"):
            with st.expander(f"📌 Added to session ({len(st.session_state['_discovery_added'])})", expanded=True):
                for entry in st.session_state["_discovery_added"]:
                    st.markdown(f"- `{entry['id']}` — **{entry['name']}** ({entry['domain']})")
                if st.button("Clear session additions"):
                    st.session_state["_discovery_added"] = []
                    st.rerun()

def _add_to_session(dataset_id: str, domain: str, name: str) -> None:
    if "_discovery_added" not in st.session_state:
        st.session_state["_discovery_added"] = []
    existing = [e["id"] for e in st.session_state["_discovery_added"]]
    if dataset_id not in existing:
        st.session_state["_discovery_added"].append({
            "id": dataset_id,
            "domain": domain,
            "name": name,
        })
        st.success(f"Added `{dataset_id}` to session.", icon="✅")
    else:
        st.info(f"`{dataset_id}` is already in your session.")

def _render_soql_tab() -> None:
    st.markdown("#### SoQL Query Builder")
    st.caption(
        "Full SoQL support: `=` `!=` `>` `<` `>=` `<=` `contains` `not_like` `starts_with` "
        "`between` `in` `not_in` `is_null` `is_not_null` • `$select` `$where` `$order` "
        "`$group` `$having` `$q` `$limit` `$offset` `DISTINCT` • "
        "Geospatial: `within_circle` `within_box` `within_polygon` `distance_in_meters` • "
        "Date: `date_extract_y/m/d/dow` `date_trunc_y/ym/ymd`"
    )

    domain_in = st.text_input(
        "Domain", value=_DEFAULT_DOMAIN, key="soql_domain",
        help="Socrata portal domain.",
    )
    fourfour_in = st.text_input(
        "Dataset ID (four-four)", placeholder="e.g. dntt-gqwq", key="soql_fourfour",
        help="The 4x4 identifier from the dataset URL.",
    )

    if not fourfour_in:
        st.info("Enter a Dataset ID above to build a query. You can copy IDs from the Search tab.")
        _show_quick_ids()
        return

    # Load columns from metadata
    if st.button("📋 Load columns from dataset", key="soql_load_cols"):
        with st.spinner("Fetching metadata…"):
            meta = _fetch_metadata(domain_in, fourfour_in)
        if "error" in meta:
            st.error(meta["error"])
        else:
            cols = [c["fieldName"] for c in meta.get("columns", [])]
            st.session_state["_soql_columns"] = cols
            st.session_state["_soql_col_types"] = {
                c["fieldName"]: c.get("dataTypeName", "text")
                for c in meta.get("columns", [])
            }
            st.success(f"Loaded {len(cols)} columns.")

    available_cols = st.session_state.get("_soql_columns", [])
    col_types = st.session_state.get("_soql_col_types", {})

    if available_cols:
        st.caption("Columns: " + ", ".join(f"`{c}`" for c in available_cols[:20])
                   + (" …" if len(available_cols) > 20 else ""))

    # Condition builder
    st.markdown("**Filter conditions** (all joined with AND)")
    if "_soql_conditions" not in st.session_state:
        st.session_state["_soql_conditions"] = [{"field": "", "op": "=", "value": ""}]

    ops = [
        "=", "!=", ">", "<", ">=", "<=",
        "contains", "not_like", "starts_with", "not_starts_with",
        "between", "not_between", "in", "not_in",
        "is_null", "is_not_null",
    ]

    for i, cond in enumerate(st.session_state["_soql_conditions"]):
        c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
        field_opts = available_cols if available_cols else []
        if field_opts:
            fi = field_opts.index(cond["field"]) if cond["field"] in field_opts else 0
            cond["field"] = c1.selectbox("Field", field_opts, index=fi, key=f"sq_field_{i}")
        else:
            cond["field"] = c1.text_input("Field", value=cond.get("field", ""), key=f"sq_field_{i}")

        op_i = ops.index(cond["op"]) if cond["op"] in ops else 0
        cond["op"] = c2.selectbox("Operator", ops, index=op_i, key=f"sq_op_{i}")

        needs_value = cond["op"] not in ("is_null", "is_not_null")
        no_value_hint = {"between": "low,high", "not_between": "low,high",
                         "in": "val1,val2,val3", "not_in": "val1,val2,val3"}.get(cond["op"], "")
        if needs_value:
            cond["value"] = c3.text_input(
                "Value", value=cond.get("value", ""), key=f"sq_val_{i}",
                placeholder=no_value_hint or "",
                help=no_value_hint if no_value_hint else None,
            )
        else:
            c3.markdown("*(no value)*")
            cond["value"] = ""

        if c4.button("🗑", key=f"sq_del_{i}", help="Remove condition"):
            st.session_state["_soql_conditions"].pop(i)
            st.rerun()

    col_add, col_clear = st.columns(2)
    if col_add.button("➕ Add condition"):
        st.session_state["_soql_conditions"].append({"field": "", "op": "=", "value": ""})
        st.rerun()
    if col_clear.button("🗑 Clear all conditions"):
        st.session_state["_soql_conditions"] = [{"field": "", "op": "=", "value": ""}]
        st.rerun()

    # Extra SoQL clauses
    with st.expander("Additional clauses — $select, $group, $having, $q, DISTINCT"):
        xc1, xc2 = st.columns(2)
        select_clause = xc1.text_input(
            "$select", placeholder="borough, count(*) as cnt, avg(condition_score) as avg_score",
            help="Comma-separated fields or aggregate expressions. Leave blank for *.",
        )
        group_clause = xc2.text_input(
            "$group", placeholder="borough",
            help="GROUP BY fields (comma-separated). Required when using aggregate functions in $select.",
        )
        having_clause = xc1.text_input(
            "$having", placeholder="count(*) > 100",
            help="Filter on aggregate results (applied after GROUP BY).",
        )
        q_clause = xc2.text_input(
            "$q (full-text search)", placeholder="sidewalk defect",
            help="Full-text search across all text fields in the dataset (SODA 2.x).",
        )
        xc3, xc4 = st.columns(2)
        distinct_toggle = xc3.checkbox(
            "DISTINCT", value=False,
            help="Return only unique rows ($select distinct). Prepends DISTINCT to $select.",
        )
        order_clause = xc3.text_input(
            "$order", placeholder="inspection_date DESC",
            help="Sort expression, e.g. `count(*) DESC` or `borough ASC`.",
        )
        limit_clause = xc4.number_input("$limit", min_value=1, max_value=50_000, value=1_000, step=500)
        offset_clause = xc4.number_input("$offset", min_value=0, value=0, step=limit_clause)

    # Geospatial query helper
    with st.expander("🌐 Geospatial query helper (within_circle / within_box)"):
        st.caption(
            "Generate a geospatial WHERE clause. The dataset must have a Point geometry column. "
            "Use `within_circle(geom_col, lat, lon, radius_m)` or "
            "`within_box(geom_col, lat_min, lon_min, lat_max, lon_max)`."
        )
        geo_col = st.text_input("Geometry column name", value="the_geom", key="geo_col")
        geo_type = st.radio("Function", ["within_circle", "within_box", "distance_in_meters"], horizontal=True, key="geo_type")
        if geo_type == "within_circle":
            gc1, gc2, gc3 = st.columns(3)
            gc_lat = gc1.number_input("Center latitude", value=40.7128, format="%.6f", key="gc_lat")
            gc_lon = gc2.number_input("Center longitude", value=-74.0060, format="%.6f", key="gc_lon")
            gc_rad = gc3.number_input("Radius (meters)", value=1000, min_value=1, key="gc_rad")
            geo_expr = f"within_circle({geo_col}, {gc_lat}, {gc_lon}, {gc_rad})"
        elif geo_type == "within_box":
            gb1, gb2 = st.columns(2)
            gb_lat1 = gb1.number_input("SW latitude", value=40.70, format="%.6f", key="gb_lat1")
            gb_lon1 = gb1.number_input("SW longitude", value=-74.02, format="%.6f", key="gb_lon1")
            gb_lat2 = gb2.number_input("NE latitude", value=40.73, format="%.6f", key="gb_lat2")
            gb_lon2 = gb2.number_input("NE longitude", value=-73.97, format="%.6f", key="gb_lon2")
            geo_expr = f"within_box({geo_col}, {gb_lat1}, {gb_lon1}, {gb_lat2}, {gb_lon2})"
        else:
            gd1, gd2, gd3 = st.columns(3)
            gd_col2 = gd1.text_input("Second geometry column", value="location", key="gd_col2")
            gd_max = gd2.number_input("Max distance (meters)", value=500, min_value=1, key="gd_max")
            geo_expr = f"distance_in_meters({geo_col}, {gd_col2}) <= {gd_max}"
        st.code(geo_expr, language="sql")
        if st.button("📋 Append to WHERE conditions", key="geo_append"):
            if "_soql_conditions" not in st.session_state:
                st.session_state["_soql_conditions"] = []
            st.session_state["_soql_conditions"].append({"field": "__geo__", "op": "=", "value": "", "_raw": geo_expr})
            st.success(f"Appended: `{geo_expr}`")
            st.rerun()

    # Date function reference
    with st.expander("📅 Date function reference"):
        st.caption("Use these in $select, $where, or $order. Example: `date_extract_y(inspection_date) = 2024`")
        st.markdown("""
| Function | Returns | Example |
|----------|---------|---------|
| `date_extract_y(col)` | Year (int) | `date_extract_y(inspection_date) = 2024` |
| `date_extract_m(col)` | Month 1–12 | `date_extract_m(inspection_date) = 6` |
| `date_extract_d(col)` | Day 1–31 | `date_extract_d(inspection_date) > 15` |
| `date_extract_dow(col)` | Day of week 0–6 | `date_extract_dow(inspection_date) = 1` |
| `date_extract_woy(col)` | Week of year 0–51 | |
| `date_extract_hh(col)` | Hour 0–23 | |
| `date_trunc_y(col)` | Truncate to year | `$group=date_trunc_y(inspection_date)` |
| `date_trunc_ym(col)` | Truncate to month | `$select=date_trunc_ym(inspection_date) as month, count(*)` |
| `date_trunc_ymd(col)` | Truncate to day | |
        """)

    # String / numeric function reference
    with st.expander("🔤 String & aggregate function reference"):
        st.markdown("""
**String:** `upper(col)` `lower(col)` `unaccent(col)` `starts_with(col, 'prefix')` `col like '%pattern%'`

**Aggregate (use with $group):** `count(*)` `sum(col)` `avg(col)` `min(col)` `max(col)` `stddev_pop(col)` `stddev_samp(col)`

**Numeric:** `ln(col)` `greatest(a, b)` `least(a, b)`

**Conditional:** `case(condition, true_val, false_val)` `col between a and b` `col in('a','b','c')`

**Geospatial:** `within_circle(geom, lat, lon, meters)` `within_box(geom, lat1, lon1, lat2, lon2)` `within_polygon(geom, wkt_polygon)` `distance_in_meters(geom1, geom2)` `intersects(geom1, geom2)`

**DISTINCT:** Prefix $select value with `distinct ` or use the DISTINCT checkbox above.
        """)

    # Merge regular conditions + any raw geo expressions
    regular_conds = [c for c in st.session_state["_soql_conditions"] if "_raw" not in c]
    raw_parts = [c["_raw"] for c in st.session_state["_soql_conditions"] if "_raw" in c]
    where_str = _build_soql(regular_conds)
    if raw_parts:
        where_str = " AND ".join(filter(None, [where_str] + raw_parts))

    # Build $select with optional DISTINCT prefix
    effective_select = select_clause
    if distinct_toggle and effective_select:
        effective_select = f"distinct {effective_select}"
    elif distinct_toggle:
        effective_select = "distinct *"

    # Preview the generated URL
    base_url = f"https://{domain_in}/resource/{fourfour_in}.json"
    qs_parts = []
    if where_str:
        qs_parts.append(f"$where={requests.utils.quote(where_str)}")
    if effective_select:
        qs_parts.append(f"$select={requests.utils.quote(effective_select)}")
    if group_clause:
        qs_parts.append(f"$group={requests.utils.quote(group_clause)}")
    if having_clause:
        qs_parts.append(f"$having={requests.utils.quote(having_clause)}")
    if order_clause:
        qs_parts.append(f"$order={requests.utils.quote(order_clause)}")
    if q_clause:
        qs_parts.append(f"$q={requests.utils.quote(q_clause)}")
    qs_parts.append(f"$limit={limit_clause}&$offset={int(offset_clause)}")
    preview_url = base_url + ("?" + "&".join(qs_parts) if qs_parts else "")

    st.markdown("**Generated WHERE clause:**")
    st.code(where_str or "(none — all rows)", language="sql")
    st.markdown("**Full API URL:**")
    st.code(preview_url, language="text")

    if st.button("▶ Run query", type="primary"):
        if not fourfour_in:
            st.warning("Enter a Dataset ID first.")
            return
        with st.spinner("Fetching data from Socrata…"):
            params: dict[str, Any] = {"$limit": limit_clause, "$offset": int(offset_clause)}
            if where_str:
                params["$where"] = where_str
            if effective_select:
                params["$select"] = effective_select
            if group_clause:
                params["$group"] = group_clause
            if having_clause:
                params["$having"] = having_clause
            if order_clause:
                params["$order"] = order_clause
            if q_clause:
                params["$q"] = q_clause
            try:
                r = requests.get(
                    f"https://{domain_in}/resource/{fourfour_in}.json",
                    params=params,
                    headers={**_headers(), "Accept": "application/json"},
                    timeout=20,
                )
                if r.status_code == 429:
                    st.error(
                        "⚠️ Rate limited (HTTP 429). Add your Socrata App Token in "
                        "⚙️ Settings → 🔑 API Tokens to get a dedicated request pool with no throttling."
                    )
                    return
                r.raise_for_status()
                df = pd.DataFrame(r.json())
                st.success(f"Returned {len(df):,} rows.")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇ Export (CSV)",
                    df.to_csv(index=False).encode("utf-8"),
                    f"{fourfour_in}_query.csv",
                    mime="text/csv",
                )
                st.session_state[f"_discovery_query_{fourfour_in}"] = df
                st.caption(f"Saved as `_discovery_query_{fourfour_in}` in session state.")
            except Exception as exc:
                st.error(f"Query failed: {exc}")

def _show_quick_ids() -> None:
    """Show the registered dataset IDs for quick copy."""
    from app.data_loader import DATASET_REGISTRY
    rows = [
        {"key": k, "id": v["fourfour"], "label": v.get("label", k), "group": v.get("group", "")}
        for k, v in DATASET_REGISTRY.items()
    ]
    if rows:
        st.markdown("**Registered datasets (quick-copy IDs):**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def _render_preview_tab() -> None:
    st.markdown("#### Dataset Preview")
    st.caption("Inspect schema and sample rows for any Socrata dataset.")

    # Prefill from search tab
    default_id = st.session_state.get("_discovery_preview_id", "")
    default_domain = st.session_state.get("_discovery_preview_domain", _DEFAULT_DOMAIN)
    default_name = st.session_state.get("_discovery_preview_name", "")

    if default_name:
        st.info(f"Previewing: **{default_name}**")

    p_col1, p_col2 = st.columns(2)
    domain_p = p_col1.text_input("Domain", value=default_domain, key="prev_domain")
    fourfour_p = p_col2.text_input("Dataset ID", value=default_id, key="prev_fourfour",
                                    placeholder="e.g. dntt-gqwq")

    if not fourfour_p:
        _show_quick_ids()
        return

    sample_limit = st.slider("Sample rows", 5, 200, 25, step=5)

    col_meta, col_sample = st.columns(2)

    with col_meta:
        if st.button("📄 Load metadata", key="prev_load_meta", use_container_width=True):
            with st.spinner("Fetching metadata…"):
                meta = _fetch_metadata(domain_p, fourfour_p)
            if "error" in meta:
                st.error(meta["error"])
            else:
                st.success(f"**{meta.get('name', fourfour_p)}**")
                st.caption(meta.get("description", "No description.")[:400])
                created = (meta.get("createdAt") or "")[:10]
                updated = (meta.get("rowsUpdatedAt") or meta.get("updatedAt") or "")[:10]
                row_count = meta.get("cachedContents", {}).get("non_null", "?")
                st.markdown(
                    f"Created: `{created}` | Updated: `{updated}` | Rows: `{row_count}`"
                )
                cols = meta.get("columns", [])
                if cols:
                    col_df = pd.DataFrame([{
                        "field": c["fieldName"],
                        "type": c.get("dataTypeName", ""),
                        "description": (c.get("description") or "")[:80],
                    } for c in cols])
                    st.markdown(f"**{len(cols)} columns:**")
                    st.dataframe(col_df, use_container_width=True, hide_index=True, height=300)

    with col_sample:
        if st.button("📊 Load sample rows", key="prev_load_sample", use_container_width=True):
            with st.spinner("Fetching sample…"):
                df = _fetch_sample(domain_p, fourfour_p, sample_limit)
            if "error" in df.columns:
                st.error(df["error"].iloc[0])
            else:
                st.success(f"{len(df)} rows × {len(df.columns)} columns")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇ Export sample (CSV)",
                    df.to_csv(index=False).encode("utf-8"),
                    f"{fourfour_p}_sample.csv",
                    mime="text/csv",
                )

# --------------------------------------------------------------------------- #
# NL Query helpers
# --------------------------------------------------------------------------- #

_SAVED_QUERIES_PATH = Path("data/saved_queries.json")
_NL_HISTORY_KEY = "nl_query_history"
_MAX_HISTORY = 20

def _load_saved_queries() -> list[dict[str, Any]]:
    """Load saved queries from disk. Returns empty list on error."""
    try:
        if _SAVED_QUERIES_PATH.exists():
            with _SAVED_QUERIES_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        pass
    return []

def _save_query_to_disk(question: str, dataset_key: str, soql_params: dict[str, Any]) -> None:
    """Persist a favorite query to data/saved_queries.json."""
    _SAVED_QUERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_saved_queries()
    entry: dict[str, Any] = {
        "question": question,
        "dataset_key": dataset_key,
        "soql_params": soql_params,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    existing.append(entry)
    with _SAVED_QUERIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

def _nl_session_with_retry() -> requests.Session:
    """Return a requests.Session with retry logic."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_nl_results(
    domain: str,
    fourfour: str,
    select: str,
    where: str,
    group: str,
    order: str,
    limit: str,
) -> pd.DataFrame:
    """Fetch Socrata data using SoQL params from NL translation."""
    url = f"https://{domain}/resource/{fourfour}.json"
    params: dict[str, Any] = {}
    if select:
        params["$select"] = select
    if where:
        params["$where"] = where
    if group:
        params["$group"] = group
    if order:
        params["$order"] = order
    if limit and str(limit).isdigit():
        params["$limit"] = limit
    else:
        params["$limit"] = "100"

    token = os.getenv("SOCRATA_APP_TOKEN", "").strip() or None
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["X-App-Token"] = token

    session = _nl_session_with_retry()
    try:
        r = session.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except requests.exceptions.HTTPError as exc:
        return pd.DataFrame({"error": [f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"]})
    except requests.exceptions.Timeout:
        return pd.DataFrame({"error": ["Request timed out (20 s)."]})
    except Exception as exc:
        return pd.DataFrame({"error": [str(exc)]})

def _get_dataset_registry_keys() -> list[str]:
    """Return dataset keys from DATASET_REGISTRY."""
    try:
        from app.data_loader import DATASET_REGISTRY  # noqa: PLC0415
        return list(DATASET_REGISTRY.keys())
    except Exception:
        return []

def _get_columns_for_dataset(dataset_key: str) -> list[str]:
    """Fetch column names for a registered dataset via Socrata metadata."""
    try:
        from app.data_loader import DATASET_REGISTRY  # noqa: PLC0415
        meta = DATASET_REGISTRY.get(dataset_key, {})
        fourfour = meta.get("fourfour", "")
        if not fourfour:
            return []
        fetched = _fetch_metadata(_DEFAULT_DOMAIN, fourfour)
        return [c["fieldName"] for c in fetched.get("columns", [])]
    except Exception:
        return []

def _render_nl_query_tab() -> None:
    st.markdown("#### 🤖 Natural Language Query")
    st.caption(
        "Ask a question in plain English and get results from NYC Open Data. "
        "Powered by Claude AI — translates your question into a SoQL query automatically."
    )

    if not HAS_ANTHROPIC:
        st.warning(
            "Install anthropic package to use NL queries: pip install anthropic",
            icon="⚠️",
        )
        return

    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        st.warning(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it to enable natural language queries.",
            icon="⚠️",
        )

    # Initialize session state
    if _NL_HISTORY_KEY not in st.session_state:
        st.session_state[_NL_HISTORY_KEY] = []

    # ---- Saved / favorite queries ----
    saved_queries = _load_saved_queries()
    prefill_question = ""
    prefill_dataset = ""

    if saved_queries:
        with st.expander(f"⭐ Saved queries ({len(saved_queries)})", expanded=False):
            labels = [
                f"{q['question'][:60]} [{q['dataset_key']}]"
                for q in saved_queries
            ]
            selected_fav = st.selectbox(
                "Load a saved query",
                options=["— select —"] + labels,
                key="nl_fav_selectbox",
            )
            if selected_fav and selected_fav != "— select —":
                idx = labels.index(selected_fav)
                fav = saved_queries[idx]
                prefill_question = fav["question"]
                prefill_dataset = fav["dataset_key"]
                st.info(
                    f"Loaded: **{fav['question']}** on `{fav['dataset_key']}` "
                    f"(saved {fav.get('saved_at', '')[:10]})"
                )

    # ---- Dataset selector ----
    registry_keys = _get_dataset_registry_keys()
    if not registry_keys:
        registry_keys = ["inspection"]

    default_ds_idx = 0
    if prefill_dataset and prefill_dataset in registry_keys:
        default_ds_idx = registry_keys.index(prefill_dataset)

    col_ds, col_q = st.columns([2, 4])
    selected_dataset = col_ds.selectbox(
        "Dataset",
        options=registry_keys,
        index=default_ds_idx,
        key="nl_dataset_select",
        help="Select the dataset to query.",
    )

    # ---- Query input ----
    question = col_q.text_input(
        "Ask a question about your data",
        value=prefill_question,
        key="nl_query_input",
        placeholder=(
            "e.g. How many inspections per borough? "
            "Show me the 10 most recent violations in Manhattan."
        ),
    )

    run_col, _ = st.columns([1, 4])
    run_query = run_col.button("▶ Run NL Query", type="primary", use_container_width=True)

    if not run_query:
        # Show query history if any
        _render_nl_history()
        return

    if not question.strip():
        st.warning("Enter a question to continue.")
        return

    # Fetch columns for the selected dataset
    with st.spinner("Loading dataset columns…"):
        columns = _get_columns_for_dataset(selected_dataset)

    if not columns:
        st.info(
            f"Could not load columns for `{selected_dataset}`. "
            "The query will proceed with all columns (*)."
        )

    # Translate NL → SoQL
    try:
        with st.spinner("Translating question to SoQL via Claude…"):
            soql_params = nl_to_soql(
                question=question,
                dataset_key=selected_dataset,
                columns=columns,
            )
    except RuntimeError as exc:
        st.error(f"NL translation failed: {exc}")
        return

    # Validate
    validation_errors = validate_soql(soql_params, columns)
    if validation_errors:
        st.warning("Validation issues with generated query:")
        for err in validation_errors:
            st.caption(f"- {err}")

    # Show generated SoQL
    with st.expander("📄 Generated SoQL params", expanded=True):
        st.code(json.dumps(soql_params, indent=2), language="json")

    # Fetch from Socrata
    try:
        from app.data_loader import DATASET_REGISTRY  # noqa: PLC0415
        meta = DATASET_REGISTRY.get(selected_dataset, {})
        domain = _DEFAULT_DOMAIN
        fourfour = meta.get("fourfour", "")
    except Exception:
        domain = _DEFAULT_DOMAIN
        fourfour = ""

    if not fourfour:
        st.error(f"No dataset ID (four-four) found for `{selected_dataset}`.")
        return

    with st.spinner("Fetching results from Socrata…"):
        result_df = _fetch_nl_results(
            domain=domain,
            fourfour=fourfour,
            select=soql_params.get("select", ""),
            where=soql_params.get("where", ""),
            group=soql_params.get("group", ""),
            order=soql_params.get("order", ""),
            limit=str(soql_params.get("limit", "100")),
        )

    if "error" in result_df.columns:
        st.error(f"Query failed: {result_df['error'].iloc[0]}")
        return

    st.success(f"Returned **{len(result_df):,}** row(s).")
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    # ---- Save to history ----
    history_entry: dict[str, Any] = {
        "question": question,
        "dataset_key": selected_dataset,
        "soql_params": soql_params,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    history: list[dict[str, Any]] = st.session_state[_NL_HISTORY_KEY]
    history.insert(0, history_entry)
    st.session_state[_NL_HISTORY_KEY] = history[:_MAX_HISTORY]

    # ---- Save to favorites button ----
    if st.button("⭐ Save query", key="nl_save_fav"):
        _save_query_to_disk(question, selected_dataset, soql_params)
        st.success("Query saved to favorites.")

    # ---- Show history ----
    _render_nl_history()

def _render_nl_history() -> None:
    """Render the NL query history panel."""
    history: list[dict[str, Any]] = st.session_state.get(_NL_HISTORY_KEY, [])
    if not history:
        return

    with st.expander(f"🕑 Query history ({len(history)})", expanded=False):
        for i, entry in enumerate(history):
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            st.markdown(
                f"**{i + 1}.** `{entry['dataset_key']}` — {entry['question']}  "
                f"<small>{ts} UTC</small>",
                unsafe_allow_html=True,
            )
            st.code(json.dumps(entry["soql_params"], indent=2), language="json")
            st.divider()
