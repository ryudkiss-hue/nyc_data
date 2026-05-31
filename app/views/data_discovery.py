"""Socrata Discovery — search and browse open datasets across NYC Open Data."""

from __future__ import annotations

import os
import re
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

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
        if not field or not value:
            continue
        if op == "=":
            parts.append(f"{field} = '{value}'")
        elif op == "!=":
            parts.append(f"{field} != '{value}'")
        elif op == "contains":
            parts.append(f"upper({field}) like upper('%{value}%')")
        elif op == "starts_with":
            parts.append(f"starts_with(upper({field}), upper('{value}'))")
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

    tab_search, tab_builder, tab_preview = st.tabs([
        "🔎 Search & Filter",
        "🛠️ SoQL Query Builder",
        "📋 Dataset Preview",
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
        "Build filter queries for any Socrata dataset. "
        "SoQL supports `=`, `!=`, `LIKE` (via contains/starts_with), comparison operators, "
        "and `IS NULL` / `IS NOT NULL`. No native regex — use client-side filtering in the Search tab."
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

    ops = ["=", "!=", "contains", "starts_with", ">", "<", ">=", "<=", "is_null", "is_not_null"]

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
        if needs_value:
            cond["value"] = c3.text_input("Value", value=cond.get("value", ""), key=f"sq_val_{i}")
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
    with st.expander("Additional clauses"):
        select_clause = st.text_input(
            "$select", placeholder="field1, field2, count(*) as cnt",
            help="Comma-separated fields. Leave blank for all (*).",
        )
        order_clause = st.text_input(
            "$order", placeholder="inspection_date DESC",
            help="Sort expression.",
        )
        limit_clause = st.number_input("$limit", min_value=1, max_value=50_000, value=1_000, step=500)
        offset_clause = st.number_input("$offset", min_value=0, value=0, step=limit_clause)

    where_str = _build_soql(st.session_state["_soql_conditions"])

    # Preview the generated URL
    base_url = f"https://{domain_in}/resource/{fourfour_in}.json"
    qs_parts = []
    if where_str:
        qs_parts.append(f"$where={requests.utils.quote(where_str)}")
    if select_clause:
        qs_parts.append(f"$select={requests.utils.quote(select_clause)}")
    if order_clause:
        qs_parts.append(f"$order={requests.utils.quote(order_clause)}")
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
            if select_clause:
                params["$select"] = select_clause
            if order_clause:
                params["$order"] = order_clause
            try:
                r = requests.get(
                    f"https://{domain_in}/resource/{fourfour_in}.json",
                    params=params,
                    headers={**_headers(), "Accept": "application/json"},
                    timeout=20,
                )
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
                # Save to session for use in other views
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
