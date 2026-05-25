from __future__ import annotations

import json

from app.views import studio


def _cart():
    return {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": "Sidewalk Inspections",
            "description": "Inspection records",
            "metadata": {
                "fourfour": "abcd-1234",
                "name": "Sidewalk Inspections",
                "columns": [
                    {"fieldName": "bbl", "dataTypeName": "text", "description": "Borough block lot"},
                    {"fieldName": "inspection_no", "dataTypeName": "text"},
                    {"fieldName": "the_geom", "dataTypeName": "point"},
                ],
            },
        },
        "wxyz-9876": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "wxyz-9876",
            "name": "Repair Permits",
            "description": "Permit records",
            "metadata": {
                "fourfour": "wxyz-9876",
                "name": "Repair Permits",
                "columns": [
                    {"fieldName": "bbl", "dataTypeName": "text"},
                    {"fieldName": "permit_number", "dataTypeName": "text"},
                ],
            },
        },
    }


def test_infer_relationships_uses_shared_civic_keys():
    relationships = studio._infer_relationships(_cart())

    assert relationships == [
        {
            "left_id": "abcd-1234",
            "left_name": "Sidewalk Inspections",
            "right_id": "wxyz-9876",
            "right_name": "Repair Permits",
            "column": "bbl",
        }
    ]


def test_extract_points_from_multiple_socrata_shapes():
    points = studio._extract_points_from_records(
        [
            {"latitude": "40.7", "longitude": "-74.0"},
            {"the_geom": {"coordinates": [-73.9, 40.8]}},
            {"location": {"latitude": "40.75", "longitude": "-73.95"}},
            {"latitude": "bad", "longitude": "-74.0"},
        ]
    )

    assert len(points) == 3
    assert set(points.columns) == {"lat", "lon"}


def test_pipeline_and_export_generators_include_cart_context():
    cart = _cart()
    relationships = studio._infer_relationships(cart)

    pandas_code = studio._build_pandas_pipeline(cart, relationships)
    sql = studio._build_postgis_sql(cart, relationships)
    dbt = studio._build_dbt_sources(cart)
    notebook = json.loads(studio._build_notebook(cart, relationships))

    assert "abcd-1234.json" in pandas_code
    assert "merge" in pandas_code
    assert "CREATE TABLE IF NOT EXISTS stg_abcd_1234" in sql
    assert "LEFT JOIN stg_wxyz_9876" in sql
    assert "fourfour: abcd-1234" in dbt
    assert notebook["nbformat"] == 4
    assert "Generated from the extraction cart" in "".join(notebook["cells"][0]["source"])


def test_identifier_and_dictionary_helpers_are_safe():
    assert studio._normalise_identifier("A weird-id!") == "a_weird_id"
    html = studio._build_dictionary_html(_cart())

    assert "Mission Control Data Dictionary" in html
    assert "Sidewalk Inspections" in html
    assert "Borough block lot" in html


# ---------------------------------------------------------------------------
# _normalise_identifier edge cases
# ---------------------------------------------------------------------------


def test_normalise_identifier_empty_string_returns_dataset():
    assert studio._normalise_identifier("") == "dataset"


def test_normalise_identifier_only_special_chars_returns_dataset():
    assert studio._normalise_identifier("!!!###") == "dataset"


def test_normalise_identifier_collapses_multiple_underscores():
    assert studio._normalise_identifier("a__b___c") == "a_b_c"


def test_normalise_identifier_strips_leading_trailing_underscores():
    assert studio._normalise_identifier("__hello__") == "hello"


def test_normalise_identifier_lowercases_input():
    assert studio._normalise_identifier("UPPER-CASE") == "upper_case"


def test_normalise_identifier_preserves_digits():
    assert studio._normalise_identifier("abcd-1234") == "abcd_1234"


# ---------------------------------------------------------------------------
# _safe_entity_name
# ---------------------------------------------------------------------------


def test_safe_entity_name_normal():
    result = studio._safe_entity_name("Sidewalk Inspections", "abcd-1234")
    assert result == "SidewalkInspections"


def test_safe_entity_name_empty_uses_fallback():
    result = studio._safe_entity_name("", "abcd-1234")
    assert result == "abcd1234"


def test_safe_entity_name_truncates_at_36():
    long_name = "A" * 50
    result = studio._safe_entity_name(long_name, "fb")
    assert len(result) <= 36


def test_safe_entity_name_special_chars_stripped():
    result = studio._safe_entity_name("NYC DOT / SIM (2024)!", "fb")
    assert result == "NycDotSim2024"


# ---------------------------------------------------------------------------
# _column_name and _column_type
# ---------------------------------------------------------------------------


def test_column_name_prefers_fieldname():
    col = {"fieldName": "bbl", "name": "BBL"}
    assert studio._column_name(col) == "bbl"


def test_column_name_falls_back_to_name():
    col = {"name": "Zip Code"}
    assert studio._column_name(col) == "zip code"


def test_column_name_returns_empty_for_missing():
    assert studio._column_name({}) == ""


def test_column_type_returns_datatypename():
    col = {"dataTypeName": "number"}
    assert studio._column_type(col) == "number"


def test_column_type_defaults_to_text():
    assert studio._column_type({}) == "text"


def test_column_type_lowercases():
    col = {"dataTypeName": "FloatingTimestamp"}
    assert studio._column_type(col) == "floatingtimestamp"


# ---------------------------------------------------------------------------
# _column_profile
# ---------------------------------------------------------------------------


def test_column_profile_skips_columns_without_field_name():
    meta = {
        "name": "Test Dataset",
        "fourfour": "test-0000",
        "columns": [
            {},
            {"fieldName": "bbl", "dataTypeName": "text"},
        ],
    }
    profiles = studio._column_profile(meta)
    assert len(profiles) == 1
    assert profiles[0]["column"] == "bbl"


def test_column_profile_marks_key_candidates():
    meta = {
        "name": "Test",
        "fourfour": "test-0001",
        "columns": [
            {"fieldName": "bbl", "dataTypeName": "text"},
            {"fieldName": "project_id", "dataTypeName": "text"},
            {"fieldName": "user_id", "dataTypeName": "text"},
            {"fieldName": "record_identifier", "dataTypeName": "text"},
            {"fieldName": "name", "dataTypeName": "text"},
        ],
    }
    profiles = {p["column"]: p for p in studio._column_profile(meta)}
    assert profiles["bbl"]["is_key_candidate"] is True
    assert profiles["project_id"]["is_key_candidate"] is True
    assert profiles["user_id"]["is_key_candidate"] is True
    assert profiles["record_identifier"]["is_key_candidate"] is True
    assert profiles["name"]["is_key_candidate"] is False


def test_column_profile_marks_geo_columns():
    meta = {
        "name": "Test",
        "fourfour": "test-0002",
        "columns": [
            {"fieldName": "the_geom", "dataTypeName": "point"},
            {"fieldName": "shape", "dataTypeName": "polygon"},
            {"fieldName": "loc_field", "dataTypeName": "text"},
            {"fieldName": "name", "dataTypeName": "text"},
        ],
    }
    profiles = {p["column"]: p for p in studio._column_profile(meta)}
    assert profiles["the_geom"]["is_geo"] is True
    assert profiles["shape"]["is_geo"] is True
    assert profiles["loc_field"]["is_geo"] is True   # "location" in field name
    assert profiles["name"]["is_geo"] is False


# ---------------------------------------------------------------------------
# _health_score
# ---------------------------------------------------------------------------


def test_health_score_base_is_35():
    score = studio._health_score({})
    assert score == 35


def test_health_score_adds_for_long_description():
    result = {"description": "x" * 41}
    assert studio._health_score(result) == 50


def test_health_score_adds_for_tags():
    assert studio._health_score({"tags": ["foo"]}) == 45


def test_health_score_adds_for_category():
    assert studio._health_score({"category": "Transportation"}) == 45


def test_health_score_adds_for_page_views():
    assert studio._health_score({"page_views_last_month": 100}) == 45


def test_health_score_adds_for_meta_row_count():
    assert studio._health_score({}, {"row_count": 500}) == 45


def test_health_score_adds_for_meta_columns():
    assert studio._health_score({}, {"columns": [{"fieldName": "bbl"}]}) == 45


def test_health_score_adds_for_geo_meta():
    assert studio._health_score({}, {"is_geo": True}) == 40


def test_health_score_is_capped_at_100():
    result = {
        "description": "x" * 50,
        "tags": ["a"],
        "category": "Health",
        "page_views_last_month": 9999,
    }
    meta = {"row_count": 10000, "columns": [{}], "is_geo": True}
    assert studio._health_score(result, meta) == 100


# ---------------------------------------------------------------------------
# _infer_relationships edge cases
# ---------------------------------------------------------------------------


def test_infer_relationships_empty_cart_returns_empty():
    assert studio._infer_relationships({}) == []


def test_infer_relationships_no_shared_keys_returns_empty():
    cart = {
        "aaaa-1111": {
            "name": "Dataset A",
            "metadata": {"columns": [{"fieldName": "unique_to_a", "dataTypeName": "text"}]},
        },
        "bbbb-2222": {
            "name": "Dataset B",
            "metadata": {"columns": [{"fieldName": "unique_to_b", "dataTypeName": "text"}]},
        },
    }
    assert studio._infer_relationships(cart) == []


def test_infer_relationships_picks_alphabetically_first_shared_key():
    cart = {
        "aaaa-1111": {
            "name": "Left",
            "metadata": {
                "columns": [
                    {"fieldName": "bbl", "dataTypeName": "text"},
                    {"fieldName": "zip", "dataTypeName": "text"},
                ]
            },
        },
        "bbbb-2222": {
            "name": "Right",
            "metadata": {
                "columns": [
                    {"fieldName": "bbl", "dataTypeName": "text"},
                    {"fieldName": "zip", "dataTypeName": "text"},
                ]
            },
        },
    }
    rels = studio._infer_relationships(cart)
    assert len(rels) == 1
    assert rels[0]["column"] == "bbl"  # alphabetically first


def test_infer_relationships_includes_id_suffix_columns():
    cart = {
        "aaaa-1111": {
            "name": "Left",
            "metadata": {"columns": [{"fieldName": "permit_id", "dataTypeName": "text"}]},
        },
        "bbbb-2222": {
            "name": "Right",
            "metadata": {"columns": [{"fieldName": "permit_id", "dataTypeName": "text"}]},
        },
    }
    rels = studio._infer_relationships(cart)
    assert len(rels) == 1
    assert rels[0]["column"] == "permit_id"


# ---------------------------------------------------------------------------
# _build_graphviz
# ---------------------------------------------------------------------------


def test_build_graphviz_contains_digraph_structure():
    cart = _cart()
    rels = studio._infer_relationships(cart)
    result = studio._build_graphviz(cart, rels)

    assert "digraph G {" in result
    assert "rankdir=LR" in result
    assert "shape=record" in result
    assert "SidewalkInspections" in result
    assert "RepairPermits" in result
    assert "bbl" in result


def test_build_graphviz_empty_cart():
    result = studio._build_graphviz({}, [])
    assert result.startswith("digraph G {")
    assert result.strip().endswith("}")


def test_build_graphviz_truncates_columns_beyond_8():
    many_columns = [{"fieldName": f"col{i}", "dataTypeName": "text"} for i in range(12)]
    cart = {
        "aaaa-1111": {
            "name": "Big Dataset",
            "domain": "data.cityofnewyork.us",
            "metadata": {"columns": many_columns},
        }
    }
    result = studio._build_graphviz(cart, [])
    assert "..." in result


# ---------------------------------------------------------------------------
# _build_mermaid
# ---------------------------------------------------------------------------


def test_build_mermaid_starts_with_erdiagram():
    result = studio._build_mermaid(_cart(), studio._infer_relationships(_cart()))
    assert result.startswith("erDiagram")


def test_build_mermaid_marks_known_join_keys_as_pk():
    result = studio._build_mermaid(_cart(), studio._infer_relationships(_cart()))
    assert " PK" in result


def test_build_mermaid_includes_relationship_line():
    result = studio._build_mermaid(_cart(), studio._infer_relationships(_cart()))
    assert "}o--o{" in result


# ---------------------------------------------------------------------------
# _pg_type
# ---------------------------------------------------------------------------


def test_pg_type_known_mappings():
    assert studio._pg_type("text") == "TEXT"
    assert studio._pg_type("number") == "NUMERIC"
    assert studio._pg_type("checkbox") == "BOOLEAN"
    assert studio._pg_type("calendar_date") == "DATE"
    assert studio._pg_type("floating_timestamp") == "TIMESTAMP"
    assert studio._pg_type("point") == "GEOMETRY(Point, 4326)"
    assert studio._pg_type("polygon") == "GEOMETRY(Polygon, 4326)"
    assert studio._pg_type("multipolygon") == "GEOMETRY(MultiPolygon, 4326)"
    assert studio._pg_type("line") == "GEOMETRY(LineString, 4326)"
    assert studio._pg_type("location") == "GEOMETRY(Point, 4326)"
    assert studio._pg_type("money") == "NUMERIC"
    assert studio._pg_type("url") == "TEXT"


def test_pg_type_unknown_falls_back_to_text():
    assert studio._pg_type("wkt") == "TEXT"
    assert studio._pg_type("unknown_type") == "TEXT"


def test_pg_type_is_case_insensitive():
    assert studio._pg_type("NUMBER") == "NUMERIC"
    assert studio._pg_type("Text") == "TEXT"


# ---------------------------------------------------------------------------
# _build_airflow_dag
# ---------------------------------------------------------------------------


def test_build_airflow_dag_empty_cart_includes_return_stub():
    result = studio._build_airflow_dag({})
    assert "return {}" in result
    assert "mission_control_socrata_extract" in result


def test_build_airflow_dag_includes_dataset_urls():
    cart = _cart()
    result = studio._build_airflow_dag(cart)
    assert "abcd-1234.json" in result
    assert "wxyz-9876.json" in result
    assert "to_parquet" in result
    assert "PythonOperator" in result


# ---------------------------------------------------------------------------
# _build_postgis_sql with no column metadata (raw JSONB fallback)
# ---------------------------------------------------------------------------


def test_build_postgis_sql_no_columns_uses_jsonb_fallback():
    cart = {
        "zzzz-0000": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "zzzz-0000",
            "name": "Sparse Dataset",
            "metadata": {"columns": []},
        }
    }
    result = studio._build_postgis_sql(cart, [])
    assert "raw JSONB" in result


def test_build_postgis_sql_applies_pg_type_mapping():
    cart = {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": "Typed Dataset",
            "metadata": {
                "columns": [
                    {"fieldName": "geo_col", "dataTypeName": "point"},
                    {"fieldName": "flag", "dataTypeName": "checkbox"},
                    {"fieldName": "label", "dataTypeName": "text"},
                ]
            },
        }
    }
    result = studio._build_postgis_sql(cart, [])
    assert "GEOMETRY(Point, 4326)" in result
    assert "BOOLEAN" in result
    assert "TEXT" in result


# ---------------------------------------------------------------------------
# _build_dbt_sources description quote sanitisation
# ---------------------------------------------------------------------------


def test_build_dbt_sources_replaces_double_quotes_in_description():
    cart = {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": 'Dataset with "quoted" description',
            "description": 'A dataset with "quoted" text',
            "metadata": {},
        }
    }
    result = studio._build_dbt_sources(cart)
    assert '"quoted"' not in result
    assert "'quoted'" in result


def test_build_dbt_sources_truncates_description_at_240():
    cart = {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": "Long Description Dataset",
            "description": "x" * 300,
            "metadata": {},
        }
    }
    result = studio._build_dbt_sources(cart)
    assert "x" * 241 not in result


# ---------------------------------------------------------------------------
# _build_dictionary_html HTML escaping
# ---------------------------------------------------------------------------


def test_build_dictionary_html_escapes_html_in_name():
    cart = {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": "<script>alert('xss')</script>",
            "metadata": {"columns": []},
        }
    }
    result = studio._build_dictionary_html(cart)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_build_dictionary_html_escapes_column_descriptions():
    cart = {
        "abcd-1234": {
            "domain": "data.cityofnewyork.us",
            "fourfour": "abcd-1234",
            "name": "Safe Name",
            "metadata": {
                "columns": [
                    {"fieldName": "col", "dataTypeName": "text", "description": "<b>Bold</b>"}
                ]
            },
        }
    }
    result = studio._build_dictionary_html(cart)
    assert "<b>Bold</b>" not in result
    assert "&lt;b&gt;Bold&lt;/b&gt;" in result


# ---------------------------------------------------------------------------
# _extract_points_from_records additional edge cases
# ---------------------------------------------------------------------------


def test_extract_points_from_records_empty_list():
    points = studio._extract_points_from_records([])
    assert points.empty


def test_extract_points_from_records_no_coords_returns_empty():
    records = [{"name": "no coords here"}, {"other": "data"}]
    points = studio._extract_points_from_records(records)
    assert points.empty


def test_extract_points_from_records_uses_lng_key():
    records = [{"lat": "40.7", "lng": "-74.0"}]
    points = studio._extract_points_from_records(records)
    assert len(points) == 1
    assert abs(points.iloc[0]["lon"] - (-74.0)) < 0.001


def test_extract_points_from_records_skips_non_numeric():
    records = [
        {"latitude": "not_a_number", "longitude": "-74.0"},
        {"latitude": "40.7", "longitude": "also_bad"},
    ]
    points = studio._extract_points_from_records(records)
    assert points.empty


def test_extract_points_from_records_geom_coordinates():
    records = [{"the_geom": {"coordinates": [-74.1, 40.6]}}]
    points = studio._extract_points_from_records(records)
    assert len(points) == 1
    assert abs(points.iloc[0]["lat"] - 40.6) < 0.001
    assert abs(points.iloc[0]["lon"] - (-74.1)) < 0.001
