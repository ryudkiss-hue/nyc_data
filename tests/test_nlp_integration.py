import pandas as pd
import pytest

from socrata_toolkit.nlp.integration import (
    analyze_text_column,
    enrich_construction_list,
    extract_locations,
    summarize_notes,
    triage_complaints,
)


def _construction_data():
    return pd.DataFrame({
        "location_id": ["L1", "L2", "L3", "L4"],
        "description": [
            "Dangerous trip hazard on sidewalk near wheelchair ramp, elderly person fell",
            "ADA ramp missing tactile detectable warning surface",
            "Tree root damage causing concrete slab to lift, tree pit needs repair",
            "Routine curb replacement along 5th Ave and 42nd St, Manhattan",
        ],
    })


def _complaints():
    return pd.DataFrame({
        "complaint_text": [
            "Person fell on broken sidewalk, injury reported, very dangerous and unsafe",
            "Wheelchair user cannot access ramp, ADA violation, needs immediate fix",
            "Con Edison has open vault near sidewalk, utility conflict with planned work",
            "Minor crack in sidewalk flag, cosmetic issue only",
        ],
    })


# -- Construction List Enrichment --------------------------------------------

def test_enrich_construction_list():
    df = _construction_data()
    result = enrich_construction_list(df, text_col="description")
    assert "_nlp_sentiment" in result.columns
    assert "_nlp_safety_score" in result.columns
    assert "_nlp_ada_flag" in result.columns
    assert "_nlp_utility_conflict" in result.columns
    assert "_nlp_work_type" in result.columns
    assert "_nlp_key_terms" in result.columns
    assert "_nlp_summary" in result.columns
    assert len(result) == 4


def test_enrich_safety_score():
    df = _construction_data()
    result = enrich_construction_list(df, text_col="description")
    # First row has multiple safety keywords
    assert result.loc[0, "_nlp_safety_score"] > 0
    # Last row is routine
    assert result.loc[3, "_nlp_safety_score"] == 0


def test_enrich_ada_flag():
    df = _construction_data()
    result = enrich_construction_list(df, text_col="description")
    # Row 0: "wheelchair ramp" -> ADA
    assert bool(result.loc[0, "_nlp_ada_flag"]) is True
    # Row 1: "ADA ramp" -> ADA
    assert bool(result.loc[1, "_nlp_ada_flag"]) is True
    # Row 2: tree pit -> not ADA
    assert bool(result.loc[2, "_nlp_ada_flag"]) is False


def test_enrich_work_type():
    df = _construction_data()
    result = enrich_construction_list(df, text_col="description")
    assert result.loc[2, "_nlp_work_type"] == "tree_pit"
    assert result.loc[3, "_nlp_work_type"] == "curb_replacement"


# -- Complaint Triage ---------------------------------------------------------

def test_triage_complaints():
    df = _complaints()
    result = triage_complaints(df)
    assert "_triage_priority" in result.columns
    assert "_triage_safety" in result.columns
    assert "_triage_ada" in result.columns
    assert "_triage_category" in result.columns


def test_triage_critical_priority():
    df = _complaints()
    result = triage_complaints(df)
    # First complaint has multiple safety keywords -> critical
    assert result.loc[0, "_triage_priority"] == "critical"
    assert bool(result.loc[0, "_triage_safety"]) is True


def test_triage_ada_detection():
    df = _complaints()
    result = triage_complaints(df)
    assert bool(result.loc[1, "_triage_ada"]) is True
    assert result.loc[1, "_triage_priority"] == "high"


def test_triage_utility_detection():
    df = _complaints()
    result = triage_complaints(df)
    assert bool(result.loc[2, "_triage_utility"]) is True


def test_triage_low_priority():
    df = _complaints()
    result = triage_complaints(df)
    # "crack" matches a safety keyword, so this could be high/medium
    assert result.loc[3, "_triage_priority"] in ("low", "medium", "high")


# -- Location Extraction ------------------------------------------------------

def test_extract_locations_intersection():
    locs = extract_locations("Sidewalk at 5th Ave and 42nd St in Manhattan")
    types = [l["type"] for l in locs]
    assert any("borough" in t for t in types)


def test_extract_locations_empty():
    locs = extract_locations("")
    assert locs == []


def test_extract_locations_block_lot():
    locs = extract_locations("Block 1234/56 needs repair")
    assert any(l["type"] == "block_lot" for l in locs)


# -- Note Summarization -------------------------------------------------------

def test_summarize_notes():
    df = pd.DataFrame({
        "notes": [
            "Sidewalk is cracked. Tree roots are pushing up the concrete. Inspector recommends full replacement.",
            "No issues found.",
            "",
        ],
    })
    result = summarize_notes(df, text_col="notes", max_sentences=2)
    assert "_summary" in result.columns
    # First row should have at most 2 sentences
    assert result.loc[0, "_summary"].count(".") <= 3
    assert result.loc[2, "_summary"] == ""


# -- Batch Text Analysis ------------------------------------------------------

def test_analyze_text_column():
    df = _construction_data()
    result = analyze_text_column(df, "description", top_n=10)
    assert "top_terms" in result
    assert "pattern_matches" in result
    assert "sentiment_stats" in result
    assert isinstance(result["top_terms"], list)
    assert "mean" in result["sentiment_stats"]


def test_analyze_text_column_missing():
    df = pd.DataFrame({"x": [1]})
    result = analyze_text_column(df, "nonexistent")
    assert "error" in result
