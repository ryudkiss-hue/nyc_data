import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.analysis import parse_sim_complaints


@pytest.fixture
def sample_df():
    """Provides a sample DataFrame for testing SIM complaint parsing."""
    data = {
        "id": [1, 2, 3, 4, 5, 6, 7],
        "description": [
            "There is a large crack and a trip hazard near the curb cut. A wheelchair cannot pass.",
            "Tree root damage has caused significant uplift on the sidewalk.",
            "A large pothole is pooling water after rain.",
            "Just a simple crack, nothing major.",
            "",
            None,
            "A dangerous metal rebar is protruding from the concrete.",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_sklearn_vectorizer():
    """Mocks the TfidfVectorizer to control keyword extraction tests."""
    with patch("socrata_toolkit.analysis.TfidfVectorizer") as mock_vectorizer_class:
        mock_vectorizer_instance = MagicMock()
        mock_vectorizer_class.return_value = mock_vectorizer_instance

        mock_tfidf_matrix = MagicMock()
        mock_vectorizer_instance.fit_transform.return_value = mock_tfidf_matrix

        # Provide default empty returns, which can be overridden in specific tests
        mock_tfidf_matrix.toarray.return_value = np.array([])
        mock_vectorizer_instance.get_feature_names_out.return_value = np.array([])

        yield mock_vectorizer_instance


class TestParseSimComplaints:
    """Test suite for the parse_sim_complaints function."""

    def test_function_adds_required_columns(self, sample_df, mock_sklearn_vectorizer):
        """Test that the function adds all the required SIM-related columns."""
        result_df = parse_sim_complaints(sample_df, text_col="description")

        assert "_sim_flags" in result_df.columns
        assert "_sim_severity_score" in result_df.columns
        assert "_sim_unique_keywords" in result_df.columns
        assert "_sim_category" in result_df.columns

    def test_taxonomy_flagging(self, sample_df):
        """Test if keywords correctly trigger the domain-specific taxonomy flags."""
        result_df = parse_sim_complaints(sample_df, text_col="description")

        # Row 0: "trip hazard", "ada_accessibility", and "surface_damage"
        assert "trip_hazard" in result_df.loc[0, "_sim_flags"]
        assert "ada_accessibility" in result_df.loc[0, "_sim_flags"]
        assert "surface_damage" in result_df.loc[0, "_sim_flags"]

        # Row 1: "root_damage"
        assert result_df.loc[1, "_sim_flags"] == ["root_damage"]

        # Row 2: "surface_damage" and "water_pooling"
        assert "surface_damage" in result_df.loc[2, "_sim_flags"]
        assert "water_pooling" in result_df.loc[2, "_sim_flags"]

        # Row 4, 5 (empty/None): No flags
        assert result_df.loc[4, "_sim_flags"] == []
        assert result_df.loc[5, "_sim_flags"] == []

    def test_severity_scoring(self, sample_df):
        """Test the calculation of the severity score based on triggered flags."""
        result_df = parse_sim_complaints(sample_df, text_col="description")

        # Row 0: trip_hazard (0.4) + ada (0.35) + surface_damage (0.15) = 0.9
        assert result_df.loc[0, "_sim_severity_score"] == pytest.approx(0.9)

        # Row 1: root_damage (0.2) = 0.2
        assert result_df.loc[1, "_sim_severity_score"] == pytest.approx(0.2)

        # Row 5 (None): Should be 0.0
        assert result_df.loc[5, "_sim_severity_score"] == 0.0

    def test_categorization(self, sample_df):
        """Test the primary categorization logic based on flag combinations."""
        result_df = parse_sim_complaints(sample_df, text_col="description")

        # Row 0: trip_hazard + ada_accessibility -> critical_accessibility_hazard
        assert result_df.loc[0, "_sim_category"] == "critical_accessibility_hazard"

        # Row 1: root_damage -> root_damage
        assert result_df.loc[1, "_sim_category"] == "root_damage"

        # Row 4 (empty): unknown
        assert result_df.loc[4, "_sim_category"] == "unknown"

    def test_keyword_extraction_with_mock(self, mock_sklearn_vectorizer):
        """Test that TF-IDF is called and keywords are extracted based on mock scores."""
        df = pd.DataFrame({"description": ["wheelchair hazard crack", "just a root", "rebar metal"]})

        # Configure the mock's return values for this specific test
        scores = np.array(
            [
                [0.5, 0.8, 0.9, 0.0, 0.0, 0.0],  # doc1: wheelchair, hazard, crack
                [0.0, 0.0, 0.0, 0.9, 0.0, 0.0],  # doc2: root
                [0.0, 0.9, 0.0, 0.0, 0.8, 0.7],  # doc3: hazard, rebar, metal
            ]
        )
        features = np.array(["crack", "hazard", "wheelchair", "root", "rebar", "metal"])
        mock_sklearn_vectorizer.fit_transform.return_value.toarray.return_value = scores
        mock_sklearn_vectorizer.get_feature_names_out.return_value = features

        result_df = parse_sim_complaints(df, text_col="description")

        # Verify TfidfVectorizer was initialized and used
        mock_sklearn_vectorizer.fit_transform.assert_called_once()

        # Check the extracted keywords based on the mocked scores (top 3 sorted by score)
        assert result_df.loc[0, "_sim_unique_keywords"] == ["wheelchair", "hazard", "crack"]
        assert result_df.loc[1, "_sim_unique_keywords"] == ["root"]
        assert result_df.loc[2, "_sim_unique_keywords"] == ["hazard", "rebar", "metal"]

    def test_graceful_failure_if_sklearn_not_installed(self, sample_df, monkeypatch):
        """Test that the function returns the original df if sklearn is not found."""
        # Simulate ImportError for any sklearn module
        monkeypatch.setitem(sys.modules, "sklearn.feature_extraction.text", None)

        # The function should log an error and return the original dataframe
        result_df = parse_sim_complaints(sample_df, text_col="description")

        # Ensure no new columns were added
        assert "_sim_flags" not in result_df.columns
        # Check that the returned object is the same as the input
        pd.testing.assert_frame_equal(result_df, sample_df)

    def test_handles_missing_text_column(self, sample_df):
        """Test that the function returns a copy of the df if the text column is missing."""
        result_df = parse_sim_complaints(sample_df, text_col="non_existent_column")

        # Ensure no new columns were added
        assert "_sim_flags" not in result_df.columns
        # It should return a copy of the original dataframe
        pd.testing.assert_frame_equal(result_df, sample_df)
        # And it should be a copy, not the same object
        assert result_df is not sample_df