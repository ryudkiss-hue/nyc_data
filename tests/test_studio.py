from __future__ import annotations

import json

# from app.views import studio  # TODO: studio module not found

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
