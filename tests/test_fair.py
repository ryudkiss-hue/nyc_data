"""Tests for the FAIR metadata catalog package."""

from __future__ import annotations

from pathlib import Path

import pytest

from socrata_toolkit.fair import (
    FairCatalog,
    FairDataset,
    FairnessScore,
    SchemaField,
    from_registry_yaml,
    score_fairness,
)

REGISTRY = Path(__file__).resolve().parents[1] / "config" / "datasets.yaml"

def _full_dataset() -> FairDataset:
    return FairDataset(
        persistent_id="https://data.cityofnewyork.us/d/abcd-1234",
        title="Sidewalk Inspections",
        description="A comprehensive record of sidewalk inspections across all boroughs.",
        keywords=["sidewalk", "inspection", "nyc"],
        domain="infrastructure",
        fourfour="abcd-1234",
        landing_page="https://data.cityofnewyork.us/d/abcd-1234",
        access_url="https://data.cityofnewyork.us/resource/abcd-1234.json",
        access_protocol="SODA",
        access_rights="public",
        license="https://example.org/license",
        format="application/json",
        conforms_to="https://www.w3.org/TR/vocab-dcat-2/",
        vocabulary="http://www.w3.org/ns/dcat#",
        schema_fields=[SchemaField("borough", "string", "Borough name", "schema:Place")],
        provenance={"source": "NYC Open Data", "publisher": "City of New York"},
        usage_rights="Public domain.",
        citation="City of New York. Sidewalk Inspections. NYC Open Data.",
    )

def test_dataclass_construction():
    ds = _full_dataset()
    assert ds.title == "Sidewalk Inspections"
    assert ds.schema_fields[0].name == "borough"
    # round trip through dict
    again = FairDataset.from_dict(ds.to_dict())
    assert again == ds
    assert isinstance(again.schema_fields[0], SchemaField)

def test_scoring_full_is_high():
    score = score_fairness(_full_dataset())
    assert isinstance(score, FairnessScore)
    assert score.overall == 100
    assert score.findable == 25
    assert score.accessible == 25
    assert score.interoperable == 25
    assert score.reusable == 25
    assert score.gaps == []

def test_scoring_empty_is_low_with_gaps():
    score = score_fairness(FairDataset())
    assert score.overall == 0
    assert len(score.gaps) == 16  # 4 checks x 4 principles
    assert any("persistent_id" in g for g in score.gaps)
    assert any("license" in g for g in score.gaps)

def test_scoring_subscore_bounds():
    score = score_fairness(_full_dataset())
    for sub in (score.findable, score.accessible, score.interoperable, score.reusable):
        assert 0 <= sub <= 25

def test_catalog_add_get_list():
    cat = FairCatalog()
    ds = _full_dataset()
    ds_id = cat.add(ds, dataset_id="sidewalk")
    assert ds_id == "sidewalk"
    assert cat.get("sidewalk") is ds
    assert cat.list() == ["sidewalk"]
    assert len(cat) == 1

def test_catalog_add_requires_id():
    with pytest.raises(ValueError):
        FairCatalog().add(FairDataset())

def test_catalog_json_round_trip():
    cat = FairCatalog(title="My Catalog")
    cat.add(_full_dataset(), dataset_id="sidewalk")
    restored = FairCatalog.from_json(cat.to_json())
    assert restored.title == "My Catalog"
    assert restored.list() == ["sidewalk"]
    assert restored.get("sidewalk") == cat.get("sidewalk")

def test_score_all():
    cat = FairCatalog()
    cat.add(_full_dataset(), dataset_id="full")
    cat.add(FairDataset(persistent_id="empty"), dataset_id="empty")
    scores = cat.score_all()
    assert scores["full"].overall == 100
    assert scores["empty"].overall < 25

def test_dcat_jsonld_shape():
    cat = FairCatalog(title="DCAT Test")
    cat.add(_full_dataset(), dataset_id="sidewalk")
    doc = cat.to_dcat_jsonld()
    assert "@context" in doc
    assert "dcat" in doc["@context"]
    assert doc["@type"] == "dcat:Catalog"
    datasets = doc["dcat:dataset"]
    assert len(datasets) == 1
    node = datasets[0]
    assert node["@type"] == "dcat:Dataset"
    assert node["dct:title"] == "Sidewalk Inspections"
    assert node["dcat:keyword"] == ["sidewalk", "inspection", "nyc"]
    assert node["dcat:distribution"]["dcat:accessURL"].endswith(".json")
    # must be JSON-serializable
    import json

    json.dumps(doc)

def test_registry_bridge_on_real_config():
    assert REGISTRY.exists(), REGISTRY
    cat = from_registry_yaml(REGISTRY)
    assert len(cat) > 0
    assert "inspection" in cat.list()
    ds = cat.get("inspection")
    assert ds.fourfour == "dntt-gqwq"
    assert ds.access_url.endswith("dntt-gqwq.json")
    # every registry dataset should score reasonably (has access + license)
    scores = cat.score_all()
    assert all(s.overall > 50 for s in scores.values())

def test_registry_bridge_graceful_missing_fields(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("datasets:\n  thing:\n    label: A Thing\n", encoding="utf-8")
    cat = from_registry_yaml(p)
    ds = cat.get("thing")
    assert ds.title == "A Thing"
    assert ds.fourfour == ""
    assert ds.access_url == ""  # degraded gracefully
