import pandas as pd

from socrata_toolkit.analysis.text import generate_text_insights


def test_generate_text_insights_tags_and_regex():
    df = pd.DataFrame({
        "desc": ["Call me at 212-555-1212", "Visit https://example.org", "email a@b.com"],
        "geo": ["POINT(1 2)", None, None],
    })
    tagged, insights = generate_text_insights(df, ["desc"], geo_column="geo")
    assert len(tagged) == 3
    assert "descriptive_tags" in tagged.columns
    assert insights.regex_hits["phones"] >= 1
    assert insights.regex_hits["urls"] >= 1
