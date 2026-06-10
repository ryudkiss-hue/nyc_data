import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.analysis import (
    generate_text_insights,
    list_available_visualizations,
    parse_sim_complaints,
    profile_dataframe,
)


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
    with patch("socrata_toolkit._analysis_monolith.TfidfVectorizer") as mock_vectorizer_class:
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
        assert result_df.loc[5, "_sim_severity_score"] == float(0)

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

    def test_graceful_failure_if_sklearn_not_installed(self, sample_df):
        """Test that the function adds all required columns regardless of sklearn availability."""
        # The function should still add all required columns, with or without sklearn
        result_df = parse_sim_complaints(sample_df, text_col="description")

        # Ensure required columns are always present
        assert "_sim_flags" in result_df.columns
        assert "_sim_severity_score" in result_df.columns
        assert "_sim_category" in result_df.columns
        assert "_sim_unique_keywords" in result_df.columns

        # Verify taxonomy matching works (doesn't require sklearn)
        assert "trip_hazard" in result_df.loc[0, "_sim_flags"]
        assert "ada_accessibility" in result_df.loc[0, "_sim_flags"]

    def test_handles_missing_text_column(self, sample_df):
        """Test that the function returns a copy of the df if the text column is missing."""
        result_df = parse_sim_complaints(sample_df, text_col="non_existent_column")

        # Ensure no new columns were added
        assert "_sim_flags" not in result_df.columns
        # It should return a copy of the original dataframe
        pd.testing.assert_frame_equal(result_df, sample_df)
        # And it should be a copy, not the same object
        assert result_df is not sample_df


class TestListAvailableVisualizations:
    """Test suite for the list_available_visualizations function."""

    def test_list_available_visualizations(self):
        """Tests that the function correctly lists all public visualization functions."""
        # 1. Execution
        viz_df = list_available_visualizations()

        # 2. Assertions
        assert isinstance(viz_df, pd.DataFrame)
        assert all(col in viz_df.columns for col in ["name", "description", "parameters"])
        assert not viz_df.empty

        # Check that some known public charts are present
        known_charts = {
            "histogram",
            "bar_chart",
            "correlation_heatmap",
            "metric_status_pie_chart",
            "data_completeness_chart",
        }
        listed_charts = set(viz_df["name"])
        assert known_charts.issubset(listed_charts)

        # Check that private/helper functions are excluded
        assert "_apply_modern_layout" not in listed_charts
        assert "export_plotly_figure" not in listed_charts

        # Check a specific entry for correctness
        pie_chart_entry = viz_df[viz_df["name"] == "metric_status_pie_chart"].iloc[0]
        assert "summary" in pie_chart_entry["parameters"]
        assert "title" in pie_chart_entry["parameters"]
        assert "distribution of metric statuses" in pie_chart_entry["description"]


class TestProfileDataFrame:
    """Test suite for the profile_dataframe function."""

    @pytest.fixture
    def profile_df(self):
        """Provides a diverse DataFrame for profiling tests."""
        data = {
            "id": [1, 2, 3, 4, 5],
            "category": ["A", "B", "A", "C", "B"],
            "value": [10.1, 20.2, 30.3, 40.4, 50.5],
            "mostly_null": [None, None, None, None, "value"],
            "constant_col": ["same", "same", "same", "same", "same"],
            "date_as_object": ["2023-01-01", "2023-01-02", None, None, None],
        }
        df = pd.DataFrame(data)
        # Add a duplicate row
        return pd.concat([df, df.head(1)], ignore_index=True)

    def test_profile_counts(self, profile_df):
        """Test that row and column counts are correct."""
        profile = profile_dataframe(profile_df)
        assert profile.row_count == 6
        assert profile.column_count == 6

    def test_null_counts_and_warnings(self, profile_df):
        """Test null count calculation and high-null-value warnings."""
        profile = profile_dataframe(profile_df)

        assert profile.null_counts["mostly_null"] == 5  # 4 from original + 1 from dupe
        assert profile.null_counts["date_as_object"] == 3

        assert any("mostly_null' has high missing values (83.33%)" in w for w in profile.warnings)

    def test_constant_column_warning(self, profile_df):
        """Test that a warning is generated for constant columns."""
        profile = profile_dataframe(profile_df)
        assert any("constant_col' is constant" in w for w in profile.warnings)

    def test_date_as_object_warning(self, profile_df):
        """Test that a warning is generated for potential date columns stored as objects."""
        profile = profile_dataframe(profile_df)
        assert any("date_as_object' might be a date" in w for w in profile.warnings)

    def test_quality_score_calculation(self, profile_df):
        """Test that the quality score is calculated and penalized by warnings."""
        # Expected: 3 warnings -> 15 point penalty
        # Completeness: (36 total cells - 9 nulls) / 36 = 75%
        # Uniqueness: (6 total rows - 1 dupe) / 6 = 83.3%
        # Score = (75 * 0.6) + (83.3 * 0.4) - 15 = 45 + 33.32 - 15 = 63.32
        profile = profile_dataframe(profile_df)
        assert profile.quality_score == pytest.approx(63, abs=1)

    def test_empty_dataframe(self):
        """Test that profiling an empty DataFrame returns a valid, empty profile."""
        profile = profile_dataframe(pd.DataFrame())
        assert profile.row_count == 0
        assert profile.quality_score == 0
        assert "Input DataFrame is empty" in profile.warnings


class TestGenerateTextInsights:
    """Test suite for the generate_text_insights function."""

    @pytest.fixture
    def text_df(self):
        data = {
            "id": [1, 2, 3, 4],
            "details": [
                "The big brown fox jumps over the lazy dog.",
                "Another complaint about a big pothole.",
                "This is a test with no special terms.",
                "A big lazy cat.",
            ],
            "location": ["POINT(1 1)", None, "POINT(2 2)", None],
        }
        return pd.DataFrame(data)

    def test_vectorized_tag_generation(self, text_df):
        """Test that descriptive tags are generated correctly by the vectorized logic."""
        # "big" appears 3 times, so it should be a high-value term (3/4 > 2% of 4)
        tagged_df, insights = generate_text_insights(
            text_df, text_columns=["details"], geo_column="location"
        )

        assert "descriptive_tags" in tagged_df.columns

        # Row 0: has "big" and a geo point
        assert "big" in tagged_df.loc[0, "descriptive_tags"]
        assert "has_geo" in tagged_df.loc[0, "descriptive_tags"]

        # Row 1: has "big" but no geo point
        assert tagged_df.loc[1, "descriptive_tags"] == ["big"]

        # Row 2: has no high-value terms but has a geo point
        assert "untagged" not in tagged_df.loc[2, "descriptive_tags"]
        assert "has_geo" in tagged_df.loc[2, "descriptive_tags"]

        # Row 3: has "big" but no geo point
        assert tagged_df.loc[3, "descriptive_tags"] == ["big", "lazy"]

    def test_insights_object(self, text_df):
        """Test that the returned TextInsights object is correctly populated."""
        _, insights = generate_text_insights(text_df, text_columns=["details"])

        assert insights.row_count == 4
        assert ("big", 3) in insights.top_terms
        assert ("lazy", 2) in insights.top_terms
        # Check that the global tag list is correct
        assert "big" in insights.tags
        assert "untagged" not in insights.tags # Because every row gets at least one tag
