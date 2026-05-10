from socrata_toolkit.nlp_advanced import analyze_text, preprocess_text


def test_preprocess_text():
    tokens, lemmas = preprocess_text("The sidewalks are cracked and unsafe")
    assert "sidewalks" in tokens
    assert len(lemmas) == len(tokens)


def test_analyze_text_summary():
    out = analyze_text("Sidewalk repairs are delayed. Budget is constrained.")
    assert isinstance(out.summary, str)
    assert isinstance(out.sentiment, float)
