"""Socrata dataset architecture studio inspired by the Mission Control mockup."""

from __future__ import annotations

import html
import json
import os
import re
from dataclasses import asdict
from typing import Any

import pandas as pd
import streamlit as st

from socrata_toolkit.core import SocrataClient, SocrataConfig
from socrata_toolkit.core.models import DatasetMetadata, SearchResult

CITY_DOMAINS = {
    "NYC Open Data": "data.cityofnewyork.us",
    "Chicago Data": "data.cityofchicago.org",
    "Los Angeles Open Data": "data.lacity.org",
    "Seattle Open Data": "data.seattle.gov",
    "Austin Open Data": "data.austintexas.gov",
}

CATEGORY_OPTIONS = [
    "",
    "Transportation",
    "City Government",
    "Environment",
    "Housing & Development",
    "Public Safety",
    "Health",
    "Education",
]

KNOWN_JOIN_KEYS = {
    "bbl",
    "bblid",
    "bin",
    "borough",
    "boro",
    "block",
    "lot",
    "community_board",
    "council_district",
    "inspection_no",
    "inspection_number",
    "job_number",
    "permit_number",
    "project_id",
    "unique_key",
    "violation_number",
    "zip",
    "zipcode",
}

GEO_TYPES = {"point", "polygon", "multipolygon", "line", "location"}


def _session_key(name: str) -> str:
    return f"studio_{name}"


def _client(token: str | None = None) -> SocrataClient:
    return SocrataClient(SocrataConfig(app_token=token or os.getenv("SOCRATA_APP_TOKEN")))


def _result_to_dict(result: SearchResult) -> dict[str, Any]:
    return asdict(result)


def _metadata_to_dict(meta: DatasetMetadata) -> dict[str, Any]:
    return {
        "domain": meta.domain,
        "fourfour": meta.fourfour,
        "name": meta.name,
        "description": meta.description,
        "row_count": meta.row_count,
        "license": meta.license,
        "is_geo": meta.is_geo,
        "columns": meta.column_dict(),
    }


def _normalise_identifier(value: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "dataset"


def _safe_entity_name(name: str, fallback: str) -> str:
    compact = re.sub(r"[^0-9a-zA-Z]+", "", name.title())
    if not compact:
        compact = fallback.replace("-", "")
    return compact[:36]


def _column_name(column: dict[str, Any]) -> str:
    return str(column.get("fieldName") or column.get("name") or "").strip().lower()


def _column_type(column: dict[str, Any]) -> str:
    return str(column.get("dataTypeName") or "text").strip().lower()


def _column_profile(meta: dict[str, Any]) -> list[dict[str, Any]]:
    profiled = []
    for col in meta.get("columns", []):
        field = _column_name(col)
        if not field:
            continue
        profiled.append(
            {
                "dataset": meta["name"],
                "fourfour": meta["fourfour"],
                "column": field,
                "type": _column_type(col),
                "description": col.get("description") or "",
                "is_key_candidate": field in KNOWN_JOIN_KEYS
                or field.endswith("_id")
                or "identifier" in field,
                "is_geo": _column_type(col) in GEO_TYPES or "location" in field or field.startswith("loc_"),
            }
        )
    return profiled


def _health_score(result: dict[str, Any], meta: dict[str, Any] | None = None) -> int:
    score = 35
    if len(result.get("description") or "") > 40:
        score += 15
    if result.get("tags"):
        score += 10
    if result.get("category"):
        score += 10
    if result.get("page_views_last_month"):
        score += 10
    if meta:
        if meta.get("row_count"):
            score += 10
        if meta.get("columns"):
            score += 10
        if meta.get("is_geo"):
            score += 5
    return min(score, 100)


def _infer_relationships(cart: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    ids = list(cart.keys())
    key_sets: dict[str, set[str]] = {}
    for dataset_id, item in cart.items():
        meta = item.get("metadata") or {}
        cols = {_column_name(c) for c in meta.get("columns", [])}
        key_sets[dataset_id] = {
            c for c in cols if c in KNOWN_JOIN_KEYS or c.endswith("_id") or c.endswith("_number")
        }

    for idx, left_id in enumerate(ids):
        for right_id in ids[idx + 1 :]:
            shared = sorted(key_sets[left_id] & key_sets[right_id])
            if shared:
                relationships.append(
                    {
                        "left_id": left_id,
                        "left_name": cart[left_id].get("name", left_id),
                        "right_id": right_id,
                        "right_name": cart[right_id].get("name", right_id),
                        "column": shared[0],
                    }
                )
    return relationships


def _build_graphviz(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    lines = ["digraph G {", "  graph [rankdir=LR bgcolor=transparent];", "  node [shape=record];"]
    for dataset_id, item in cart.items():
        meta = item.get("metadata") or {}
        entity = _safe_entity_name(item.get("name", dataset_id), dataset_id)
        columns = [_column_name(c) for c in meta.get("columns", []) if _column_name(c)]
        fields = "\\l".join(columns[:8]) + ("\\l..." if len(columns) > 8 else "\\l")
        label = "{" + html.escape(item.get("name", dataset_id)) + "|" + html.escape(fields) + "}"
        lines.append(f'  {entity} [label="{label}"];')
    for rel in relationships:
        left = _safe_entity_name(rel["left_name"], rel["left_id"])
        right = _safe_entity_name(rel["right_name"], rel["right_id"])
        lines.append(f'  {left} -> {right} [label="{html.escape(rel["column"])}"];')
    lines.append("}")
    return "\n".join(lines)


def _build_mermaid(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    lines = ["erDiagram"]
    for dataset_id, item in cart.items():
        meta = item.get("metadata") or {}
        entity = _safe_entity_name(item.get("name", dataset_id), dataset_id)
        lines.append(f"  {entity} {{")
        for col in meta.get("columns", [])[:10]:
            field = _column_name(col)
            if field:
                suffix = " PK" if field in KNOWN_JOIN_KEYS else ""
                lines.append(f"    {_column_type(col)} {field}{suffix}")
        lines.append("  }")
    for rel in relationships:
        left = _safe_entity_name(rel["left_name"], rel["left_id"])
        right = _safe_entity_name(rel["right_name"], rel["right_id"])
        lines.append(f'  {left} }}o--o{{ {right} : "{rel["column"]}"')
    return "\n".join(lines)


def _pg_type(socrata_type: str) -> str:
    mapping = {
        "calendar_date": "DATE",
        "checkbox": "BOOLEAN",
        "floating_timestamp": "TIMESTAMP",
        "line": "GEOMETRY(LineString, 4326)",
        "location": "GEOMETRY(Point, 4326)",
        "money": "NUMERIC",
        "multipolygon": "GEOMETRY(MultiPolygon, 4326)",
        "number": "NUMERIC",
        "point": "GEOMETRY(Point, 4326)",
        "polygon": "GEOMETRY(Polygon, 4326)",
        "text": "TEXT",
        "url": "TEXT",
    }
    return mapping.get(socrata_type.lower(), "TEXT")


def _build_pandas_pipeline(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    lines = [
        "import pandas as pd",
        "import requests",
        "",
        "# Fetch each Socrata resource into a dataframe.",
        "APP_TOKEN = None  # Optional: set to your Socrata app token",
        "HEADERS = {'X-App-Token': APP_TOKEN} if APP_TOKEN else {}",
        "",
        "def read_socrata(url):",
        "    response = requests.get(url, headers=HEADERS, timeout=60)",
        "    response.raise_for_status()",
        "    return pd.DataFrame(response.json())",
        "",
    ]
    for dataset_id, item in cart.items():
        var = f"df_{_normalise_identifier(dataset_id).replace('_', '')[:8]}"
        url = f"https://{item['domain']}/resource/{dataset_id}.json?$limit=50000"
        lines.append(f"{var} = read_socrata({url!r})")
    if relationships:
        lines.extend(["", "# Suggested joins inferred from shared civic keys."])
        for idx, rel in enumerate(relationships, start=1):
            left = f"df_{_normalise_identifier(rel['left_id']).replace('_', '')[:8]}"
            right = f"df_{_normalise_identifier(rel['right_id']).replace('_', '')[:8]}"
            lines.append(
                f"joined_{idx} = {left}.merge({right}, on={rel['column']!r}, how='left', suffixes=('', '_right'))"
            )
    return "\n".join(lines)


def _build_airflow_dag(cart: dict[str, dict[str, Any]]) -> str:
    dataset_ids = list(cart.keys())
    lines = [
        "from __future__ import annotations",
        "",
        "from datetime import datetime",
        "import pandas as pd",
        "from airflow import DAG",
        "from airflow.operators.python import PythonOperator",
        "",
        "def extract_socrata(**_context):",
    ]
    if not dataset_ids:
        lines.append("    return {}")
    for dataset_id, item in cart.items():
        var = _normalise_identifier(dataset_id).replace("_", "")[:8]
        lines.append(
            f"    df_{var} = pd.read_json('https://{item['domain']}/resource/{dataset_id}.json?$limit=50000')"
        )
        lines.append(f"    df_{var}.to_parquet('/tmp/{var}.parquet', index=False)")
    lines.extend(
        [
            "",
            "with DAG(",
            "    dag_id='mission_control_socrata_extract',",
            "    start_date=datetime(2026, 1, 1),",
            "    schedule='@daily',",
            "    catchup=False,",
            ") as dag:",
            "    extract = PythonOperator(task_id='extract_socrata', python_callable=extract_socrata)",
        ]
    )
    return "\n".join(lines)


def _build_postgis_sql(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    lines = ["-- PostgreSQL / PostGIS staging model generated by Mission Control Studio", ""]
    aliases = {dataset_id: f"t{idx}" for idx, dataset_id in enumerate(cart.keys(), start=1)}
    for dataset_id, item in cart.items():
        meta = item.get("metadata") or {}
        table = f"stg_{_normalise_identifier(dataset_id)}"
        lines.append(f"CREATE TABLE IF NOT EXISTS {table} (")
        columns = []
        for col in meta.get("columns", [])[:50]:
            field = _normalise_identifier(_column_name(col))
            if field:
                columns.append(f"    {field} {_pg_type(_column_type(col))}")
        lines.append(",\n".join(columns or ["    raw JSONB"]))
        lines.append(");\n")
    if cart:
        first_id = next(iter(cart))
        lines.append("-- Analyst-ready join scaffold")
        lines.append(f"SELECT {aliases[first_id]}.*")
        lines.append(f"FROM stg_{_normalise_identifier(first_id)} AS {aliases[first_id]}")
        used = {first_id}
        for rel in relationships:
            if rel["left_id"] in used and rel["right_id"] not in used:
                lines.append(
                    f"LEFT JOIN stg_{_normalise_identifier(rel['right_id'])} AS {aliases[rel['right_id']]}"
                )
                lines.append(
                    f"  ON {aliases[rel['left_id']]}.{_normalise_identifier(rel['column'])} = "
                    f"{aliases[rel['right_id']]}.{_normalise_identifier(rel['column'])}"
                )
                used.add(rel["right_id"])
        lines.append("LIMIT 1000;")
    return "\n".join(lines)


def _build_dbt_sources(cart: dict[str, dict[str, Any]]) -> str:
    lines = ["version: 2", "", "sources:", "  - name: socrata", "    tables:"]
    for dataset_id, item in cart.items():
        description = (item.get("description") or "").replace('"', "'")
        lines.extend(
            [
                f"      - name: {_normalise_identifier(dataset_id)}",
                f'        description: "{description[:240]}"',
                "        meta:",
                f"          domain: {item['domain']}",
                f"          fourfour: {dataset_id}",
            ]
        )
    return "\n".join(lines)


def _build_notebook(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["# Mission Control Socrata Pipeline\n", "Generated from the extraction cart."],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": _build_pandas_pipeline(cart, relationships).splitlines(keepends=True),
        },
    ]
    return json.dumps({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}, indent=2)


def _build_dictionary_html(cart: dict[str, dict[str, Any]]) -> str:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>Mission Control Data Dictionary</title>",
        "<style>body{font-family:Arial,sans-serif;margin:2rem;}table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #ccc;padding:6px;text-align:left;}th{background:#eef2ff;}</style>",
        "</head><body><h1>Mission Control Data Dictionary</h1>",
    ]
    for dataset_id, item in cart.items():
        meta = item.get("metadata") or {}
        parts.append(f"<h2>{html.escape(item.get('name', dataset_id))} ({dataset_id})</h2>")
        parts.append(f"<p><b>Domain:</b> {html.escape(item['domain'])}</p>")
        parts.append("<table><thead><tr><th>Column</th><th>Type</th><th>Description</th></tr></thead><tbody>")
        for col in meta.get("columns", []):
            parts.append(
                "<tr>"
                f"<td>{html.escape(_column_name(col))}</td>"
                f"<td>{html.escape(_column_type(col))}</td>"
                f"<td>{html.escape(str(col.get('description') or ''))}</td>"
                "</tr>"
            )
        parts.append("</tbody></table>")
    parts.append("</body></html>")
    return "".join(parts)


def _extract_points_from_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    points: list[dict[str, Any]] = []
    for record in records:
        lat = record.get("latitude") or record.get("lat")
        lon = record.get("longitude") or record.get("lon") or record.get("lng")
        for key in ("location", "the_geom", "point"):
            geo = record.get(key)
            if isinstance(geo, dict):
                lat = lat or geo.get("latitude")
                lon = lon or geo.get("longitude")
                coords = geo.get("coordinates")
                if isinstance(coords, list) and len(coords) >= 2:
                    lon = lon or coords[0]
                    lat = lat or coords[1]
        try:
            if lat is not None and lon is not None:
                points.append({"lat": float(lat), "lon": float(lon)})
        except (TypeError, ValueError):
            continue
    return pd.DataFrame(points)


@st.cache_data(ttl=600, show_spinner=False)
def _search_catalog(
    query: str,
    domain: str,
    category: str,
    order: str,
    limit: int,
    token: str,
) -> list[dict[str, Any]]:
    results = _client(token).search(
        query=query or None,
        domain=domain,
        category=category or None,
        order=order or None,
        limit=limit,
    )
    return [_result_to_dict(r) for r in results if r.fourfour]


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_metadata(domain: str, fourfour: str, token: str) -> dict[str, Any]:
    return _metadata_to_dict(_client(token).get_metadata(domain, fourfour))


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_sample(domain: str, fourfour: str, limit: int, token: str) -> list[dict[str, Any]]:
    frame = _client(token).fetch_dataframe(domain, fourfour, max_rows=limit)
    return frame.to_dict(orient="records")


def _init_state() -> None:
    st.session_state.setdefault(_session_key("cart"), {})
    st.session_state.setdefault(_session_key("results"), [])
    st.session_state.setdefault(_session_key("workspaces"), {})
    st.session_state.setdefault(_session_key("token"), os.getenv("SOCRATA_APP_TOKEN", ""))


def _cart() -> dict[str, dict[str, Any]]:
    return st.session_state[_session_key("cart")]


def _hydrate_item(item: dict[str, Any], token: str) -> dict[str, Any]:
    if item.get("metadata"):
        return item
    item["metadata"] = _fetch_metadata(item["domain"], item["fourfour"], token)
    return item


def _add_to_cart(result: dict[str, Any], token: str) -> None:
    item = {
        "domain": result["domain"],
        "fourfour": result["fourfour"],
        "name": result["name"],
        "description": result.get("description") or "",
        "category": result.get("category") or "",
        "tags": result.get("tags") or [],
        "page_views_last_month": result.get("page_views_last_month"),
    }
    _cart()[result["fourfour"]] = _hydrate_item(item, token)


def _render_search_panel(token: str) -> None:
    with st.container(border=True):
        st.markdown("#### Discovery filters")
        domain_label = st.selectbox("City domain", list(CITY_DOMAINS), key=_session_key("domain_label"))
        domain = CITY_DOMAINS[domain_label]
        query = st.text_input("Search Socrata", placeholder="sidewalk violations, permits, trees...")
        cols = st.columns(2)
        category = cols[0].selectbox("Category", CATEGORY_OPTIONS)
        sort_label = cols[1].selectbox("Sort", ["Relevance", "Last updated", "Most viewed"])
        limit = st.slider("Catalog result limit", min_value=10, max_value=200, value=50, step=10)
        filter_cols = st.columns(3)
        use_regex = filter_cols[0].checkbox("Regex filter")
        geo_only = filter_cols[1].checkbox("Deep geo scan")
        hydrate_top = filter_cols[2].checkbox("Profile top results")

        order = {"Relevance": "", "Last updated": "updatedAt DESC", "Most viewed": "page_views_last_month DESC"}[
            sort_label
        ]
        if st.button("Search Socrata", type="primary", use_container_width=True):
            results = _search_catalog(query, domain, category, order, limit, token)
            if use_regex and query:
                try:
                    rx = re.compile(query, re.IGNORECASE)
                except re.error as exc:
                    st.error(f"Invalid regular expression: {exc}")
                    return
                results = [
                    r
                    for r in results
                    if rx.search(r.get("name") or "") or rx.search(r.get("description") or "")
                ]
            if geo_only or hydrate_top:
                profiled: list[dict[str, Any]] = []
                for result in results[: min(len(results), 25)]:
                    try:
                        result["metadata"] = _fetch_metadata(result["domain"], result["fourfour"], token)
                        if not geo_only or result["metadata"].get("is_geo"):
                            profiled.append(result)
                    except Exception:
                        if not geo_only:
                            profiled.append(result)
                results = profiled
            st.session_state[_session_key("results")] = results
            st.success(f"Found {len(results)} matching dataset(s).")


def _render_cart_panel(token: str) -> None:
    cart = _cart()
    with st.container(border=True):
        st.markdown(f"#### Extraction cart ({len(cart)})")
        if not cart:
            st.caption("Cart empty. Add datasets from Discovery.")
        for dataset_id, item in list(cart.items()):
            cols = st.columns([0.72, 0.28])
            cols[0].markdown(f"**{item['name']}**  \n`{dataset_id}`")
            if cols[1].button("Remove", key=f"remove-{dataset_id}", use_container_width=True):
                del cart[dataset_id]
                st.rerun()
        action_cols = st.columns(2)
        if action_cols[0].button("Profile cart", disabled=not cart, use_container_width=True):
            for item in cart.values():
                _hydrate_item(item, token)
            st.success("Cart profiles refreshed.")
        if action_cols[1].button("Clear", disabled=not cart, use_container_width=True):
            cart.clear()
            st.rerun()

    with st.container(border=True):
        st.markdown("#### Workspaces")
        name = st.text_input("Workspace name", placeholder="weekly-sidewalk-pack")
        cols = st.columns(2)
        if cols[0].button("Save", disabled=not cart or not name, use_container_width=True):
            st.session_state[_session_key("workspaces")][name] = json.loads(json.dumps(cart))
            st.success(f"Saved {name}.")
        workspaces = st.session_state[_session_key("workspaces")]
        if workspaces:
            choice = st.selectbox("Saved workspaces", list(workspaces))
            load_cols = st.columns(2)
            if load_cols[0].button("Load", use_container_width=True):
                st.session_state[_session_key("cart")] = json.loads(json.dumps(workspaces[choice]))
                st.rerun()
            if load_cols[1].button("Delete", use_container_width=True):
                del workspaces[choice]
                st.rerun()


def _render_export_panel(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> None:
    with st.container(border=True):
        st.markdown("#### Engineering exports")
        if not cart:
            st.caption("Add datasets to enable exports.")
            return
        dictionary_rows = []
        for item in cart.values():
            dictionary_rows.extend(_column_profile(item.get("metadata") or {}))
        csv_payload = pd.DataFrame(dictionary_rows).to_csv(index=False).encode("utf-8")
        col1, col2, col3 = st.columns(3)
        col1.download_button("CSV", csv_payload, "mission_control_dictionary.csv", use_container_width=True)
        col2.download_button(
            "JSON",
            json.dumps(cart, indent=2).encode("utf-8"),
            "mission_control_schema.json",
            "application/json",
            use_container_width=True,
        )
        col3.download_button(
            "HTML",
            _build_dictionary_html(cart).encode("utf-8"),
            "mission_control_dictionary.html",
            "text/html",
            use_container_width=True,
        )
        st.download_button(
            "Jupyter notebook",
            _build_notebook(cart, relationships).encode("utf-8"),
            "mission_control_pipeline.ipynb",
            "application/json",
            use_container_width=True,
        )


def _render_discovery_tab(results: list[dict[str, Any]], token: str) -> None:
    st.markdown("### Discovery results")
    if not results:
        st.info("Apply filters and run a Socrata search.")
        return

    rows = []
    for result in results:
        rows.append(
            {
                "health": _health_score(result, result.get("metadata")),
                "name": result["name"],
                "id": result["fourfour"],
                "domain": result["domain"],
                "category": result.get("category") or "",
                "views_last_month": result.get("page_views_last_month") or 0,
                "geo": bool((result.get("metadata") or {}).get("is_geo")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    labels = {f"{r['name']} ({r['fourfour']})": r for r in results}
    selected = st.multiselect("Add discovery result(s) to extraction cart", list(labels))
    add_cols = st.columns(2)
    if add_cols[0].button("Add selected", disabled=not selected, use_container_width=True):
        for label in selected:
            _add_to_cart(labels[label], token)
        st.success(f"Added {len(selected)} dataset(s).")
    if add_cols[1].button("Select all results", use_container_width=True):
        for result in results:
            _add_to_cart(result, token)
        st.success(f"Added {len(results)} dataset(s).")


def _render_profiles_tab(cart: dict[str, dict[str, Any]], token: str) -> None:
    st.markdown("### Metadata profiles")
    if not cart:
        st.info("Add datasets to the cart to inspect metadata.")
        return
    for item in cart.values():
        _hydrate_item(item, token)
    profile_rows = []
    for item in cart.values():
        meta = item.get("metadata") or {}
        profile_rows.append(
            {
                "dataset": item["name"],
                "id": item["fourfour"],
                "domain": item["domain"],
                "rows": meta.get("row_count"),
                "columns": len(meta.get("columns", [])),
                "geo": meta.get("is_geo"),
                "license": meta.get("license"),
            }
        )
    st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)
    dataset_label = st.selectbox(
        "Inspect columns",
        [f"{item['name']} ({dataset_id})" for dataset_id, item in cart.items()],
    )
    selected_id = dataset_label.rsplit("(", 1)[-1].rstrip(")")
    selected_meta = cart[selected_id].get("metadata") or {}
    st.dataframe(pd.DataFrame(_column_profile(selected_meta)), use_container_width=True, hide_index=True)

    if st.button("Preview live sample", key="studio-preview-sample"):
        try:
            rows = _fetch_sample(cart[selected_id]["domain"], selected_id, 25, token)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Sample fetch failed: {exc}")


def _render_diagram_tab(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> None:
    st.markdown("### ERD Studio")
    if not cart:
        st.info("Add datasets to build an ERD.")
        return
    if relationships:
        st.success(f"Inferred {len(relationships)} relationship(s) from shared civic keys.")
        st.dataframe(pd.DataFrame(relationships), use_container_width=True, hide_index=True)
    else:
        st.warning("No shared key relationships inferred yet. Add datasets with common civic identifiers.")
    graphviz = _build_graphviz(cart, relationships)
    st.graphviz_chart(graphviz, use_container_width=True)
    with st.expander("Mermaid ERD source"):
        st.code(_build_mermaid(cart, relationships), language="mermaid")


def _render_generators_tab(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> None:
    st.markdown("### Pipeline generators")
    if not cart:
        st.info("Add datasets to generate code.")
        return
    generator = st.selectbox(
        "Generator",
        ["Pandas pipeline", "Airflow DAG", "PostgreSQL / PostGIS", "dbt sources.yml"],
    )
    if generator == "Pandas pipeline":
        st.code(_build_pandas_pipeline(cart, relationships), language="python")
    elif generator == "Airflow DAG":
        st.code(_build_airflow_dag(cart), language="python")
    elif generator == "PostgreSQL / PostGIS":
        st.code(_build_postgis_sql(cart, relationships), language="sql")
    else:
        st.code(_build_dbt_sources(cart), language="yaml")


def _render_gis_tab(cart: dict[str, dict[str, Any]], token: str) -> None:
    st.markdown("### Multi-layer GIS preview")
    geo_items = {
        dataset_id: item
        for dataset_id, item in cart.items()
        if (item.get("metadata") or {}).get("is_geo")
        or any((_column_type(c) in GEO_TYPES) for c in (item.get("metadata") or {}).get("columns", []))
    }
    if not geo_items:
        st.info("No geospatial datasets in the cart. Enable Deep geo scan or add a known map dataset.")
        return
    sample_limit = st.slider("Sample rows per layer", 25, 1000, 200, step=25)
    map_frames = []
    for dataset_id, item in geo_items.items():
        try:
            rows = _fetch_sample(item["domain"], dataset_id, sample_limit, token)
            points = _extract_points_from_records(rows)
            if not points.empty:
                points["layer"] = item["name"]
                map_frames.append(points)
        except Exception as exc:
            st.warning(f"{item['name']} sample failed: {exc}")
    if not map_frames:
        st.warning("The sampled rows did not expose latitude/longitude coordinates.")
        return
    combined = pd.concat(map_frames, ignore_index=True)
    st.map(combined, latitude="lat", longitude="lon", color="layer", size=18)
    st.dataframe(combined.groupby("layer").size().reset_index(name="sampled_points"), hide_index=True)


def _render_assistant_tab(cart: dict[str, dict[str, Any]], relationships: list[dict[str, str]]) -> None:
    st.markdown("### Schema assistant")
    if not cart:
        st.info("Add datasets before composing architecture prompts.")
        return
    question = st.text_area(
        "Question for your AI/code assistant",
        placeholder="Write a PostGIS query joining these datasets by BBL and filtering Manhattan records...",
    )
    schema_lines = ["You are working with these Socrata datasets:"]
    for item in cart.values():
        meta = item.get("metadata") or {}
        columns = ", ".join(_column_name(c) for c in meta.get("columns", [])[:15] if _column_name(c))
        schema_lines.append(f"- {item['name']} ({item['domain']}/{item['fourfour']}): {columns}")
    if relationships:
        schema_lines.append("Inferred relationships:")
        schema_lines.extend(
            f"- {rel['left_name']} -> {rel['right_name']} on {rel['column']}" for rel in relationships
        )
    schema_lines.append(f"Task: {question or '[enter your task]'}")
    st.code("\n".join(schema_lines), language="markdown")
    st.caption("Copy this prompt into your approved LLM environment; API keys are not stored by the app.")


def render_studio_page() -> None:
    _init_state()
    token = st.session_state[_session_key("token")]

    st.subheader("Socrata Data Architecture Studio")
    st.caption(
        "Discover city datasets, build an extraction cart, profile schemas, infer joins, preview GIS layers, "
        "and export pipeline artifacts."
    )
    with st.expander("Configuration", expanded=False):
        st.session_state[_session_key("token")] = st.text_input(
            "Socrata App Token",
            value=token,
            type="password",
            help="Stored only in this Streamlit session and passed as X-App-Token for live API calls.",
        )
        token = st.session_state[_session_key("token")]

    cart = _cart()
    relationships = _infer_relationships(cart)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Cart datasets", len(cart))
    metric_cols[1].metric("Profiled columns", sum(len((i.get("metadata") or {}).get("columns", [])) for i in cart.values()))
    metric_cols[2].metric("Inferred joins", len(relationships))
    metric_cols[3].metric("Geo layers", sum(1 for i in cart.values() if (i.get("metadata") or {}).get("is_geo")))

    left, right = st.columns([0.34, 0.66], gap="large")
    with left:
        _render_search_panel(token)
        _render_cart_panel(token)
        _render_export_panel(cart, relationships)

    with right:
        tabs = st.tabs(["Discovery", "Profiles", "ERD Studio", "Generators", "GIS Preview", "Assistant"])
        with tabs[0]:
            _render_discovery_tab(st.session_state[_session_key("results")], token)
        with tabs[1]:
            _render_profiles_tab(cart, token)
        with tabs[2]:
            _render_diagram_tab(cart, relationships)
        with tabs[3]:
            _render_generators_tab(cart, relationships)
        with tabs[4]:
            _render_gis_tab(cart, token)
        with tabs[5]:
            _render_assistant_tab(cart, relationships)
