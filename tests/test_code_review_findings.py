"""
Verification tests for code review findings.

These tests reproduce the issues identified in code-review-report.md
to confirm they are real problems before implementation.
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest


class TestCriticalFinding1_SoQLSyntax:
    """
    Finding #1: Invalid SoQL date syntax in CLAUDE.md line 539

    Documentation shows:
        created_date>'<30d ago>'

    This test verifies whether this syntax actually works or fails.
    """

    def test_soql_relative_date_syntax_invalid(self):
        """
        Verify that Socrata SODA2 API doesn't support relative date syntax like '<30d ago>'.

        Expected: API should reject this with a syntax error.
        """
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())

        # The malformed query from documentation
        malformed_where = "upper(borough)='MANHATTAN' AND created_date>'<30d ago>'"

        # Try to fetch with the documented (broken) syntax
        with pytest.raises(Exception) as exc_info:
            # Using the actual Socrata client to test the real API
            try:
                client.fetch_dataframe(
                    domain="data.cityofnewyork.us",
                    fourfour="6kbp-uz6m",  # violations dataset
                    where=malformed_where,
                    limit=1
                )
            except Exception as e:
                # Capture what error Socrata actually returns
                error_msg = str(e)
                # Check if it's a syntax error (which we expect)
                assert "syntax" in error_msg.lower() or "invalid" in error_msg.lower() or \
                       "parse" in error_msg.lower() or "query" in error_msg.lower(), \
                       f"Expected syntax error but got: {error_msg}"
                raise

    def test_soql_iso_timestamp_syntax_valid(self):
        """
        Verify that ISO 8601 timestamps work correctly as a fix.

        This is what the documentation SHOULD show.
        """
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())

        # Generate a valid ISO 8601 timestamp from 30 days ago (seconds precision only)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")

        # The corrected query - using 311 Complaints which has 'Borough' and 'Created Date'
        valid_where = f"upper(borough)='MANHATTAN' AND created_date > '{thirty_days_ago}'"

        # This should work without raising an exception
        try:
            result = client.fetch_dataframe(
                domain="data.cityofnewyork.us",
                fourfour="erm2-nwe9", # 311 complaints
                where=valid_where,
                max_rows=1  # API uses max_rows, not limit
            )
            # If we get here without exception, the syntax is valid
            assert result is not None or isinstance(result, pd.DataFrame), \
                "Expected valid query to return a DataFrame or None (if no results)"
            print(f"[PASS] Valid ISO timestamp query works: {thirty_days_ago}")
        except Exception as e:
            pytest.fail(f"Valid ISO timestamp query failed: {e}")


class TestCriticalFinding2_SpatialIntersectsJoin:
    """
    Finding #2: Incomplete function signature in CLAUDE.md line 540

    Documentation shows:
        spatial_intersects_join(street_permits, inspection)

    But function requires:
        spatial_intersects_join(left_df, right_df, left_geom_col, right_geom_col)

    This test verifies the actual error when 2 params instead of 4 are provided.
    """

    def test_spatial_intersects_join_missing_geometry_columns(self):
        """
        Verify that calling spatial_intersects_join with only 2 params raises TypeError.
        """
        import inspect

        from socrata_toolkit.spatial.core import spatial_intersects_join

        # Get the function signature
        sig = inspect.signature(spatial_intersects_join)
        params = list(sig.parameters.keys())

        # Verify it requires 4 parameters
        assert len(params) >= 4, \
            f"spatial_intersects_join should require at least 4 params, but has: {params}"

        # Create dummy DataFrames
        left_df = pd.DataFrame({
            'id': [1, 2],
            'the_geom': ['POINT(0 0)', 'POINT(1 1)']
        })
        right_df = pd.DataFrame({
            'id': [1, 2],
            'the_geom': ['POINT(0 0)', 'POINT(2 2)']
        })

        # Try to call with only 2 params (as shown in documentation)
        # This should fail
        with pytest.raises(TypeError) as exc_info:
            spatial_intersects_join(left_df, right_df)

        # Verify the error mentions missing parameters
        error_msg = str(exc_info.value)
        assert "required" in error_msg.lower() or "missing" in error_msg.lower() or \
               "positional" in error_msg.lower(), \
               f"Expected TypeError about missing parameters, got: {error_msg}"

        print(f"[CONFIRMED] Calling with 2 params fails with: {error_msg}")

    def test_spatial_intersects_join_with_geometry_columns_works(self):
        """
        Verify that calling with 4 params (the correct way) works.
        """
        from socrata_toolkit.spatial.core import spatial_intersects_join

        # Create dummy DataFrames with geometry columns
        left_df = pd.DataFrame({
            'id': [1, 2],
            'the_geom': ['POINT(0 0)', 'POINT(1 1)'],
            'name': ['A', 'B']
        })
        right_df = pd.DataFrame({
            'id': [10, 20],
            'the_geom': ['POINT(0 0)', 'POINT(2 2)'],
            'type': ['permit', 'inspection']
        })

        # Call with all 4 required parameters
        try:
            result = spatial_intersects_join(
                left_df,
                right_df,
                left_geom_col="the_geom",
                right_geom_col="the_geom"
            )
            # If we get here, the call succeeded
            assert result is not None, "spatial_intersects_join should return a result"
            print("[PASS] Calling with 4 params works correctly")
        except TypeError as e:
            pytest.fail(f"Call with all required params should work, but got: {e}")


class TestDocumentationAccuracy:
    """
    Meta-tests to verify documentation consistency.
    """

    def test_claude_md_has_examples_that_can_be_verified(self):
        """
        Verify that CLAUDE.md code examples can be extracted and tested.
        """
        import re

        # Read CLAUDE.md
        with open("CLAUDE.md", encoding="utf-8") as f:
            claude_content = f.read()

        # Find all code blocks with SoQL
        soql_blocks = re.findall(r'```([^`]*created_date[^`]*)```', claude_content)

        assert len(soql_blocks) > 0, "CLAUDE.md should have testable SoQL examples"

        for block in soql_blocks:
            # Check for problematic patterns
            if "<30d ago>" in block:
                pytest.fail(f"Found undocumented SoQL syntax in block: {block[:100]}")

    def test_function_signatures_in_documentation_match_implementation(self):
        """
        Verify that documented function signatures match actual implementations.
        """
        import inspect

        from socrata_toolkit.spatial.core import spatial_intersects_join

        # Get actual signature
        actual_sig = str(inspect.signature(spatial_intersects_join))

        # Expected from documentation
        documented_params = ['left', 'right', 'left_geom_col', 'right_geom_col']

        # Verify all documented params exist
        for param in documented_params:
            assert param in actual_sig, \
                f"Documented parameter '{param}' not found in actual signature: {actual_sig}"


class TestDocumentationImpact:
    """
    Tests to assess the real-world impact of documentation issues.
    """

    def test_how_often_are_code_examples_used(self):
        """
        Assess: Do users actually copy code from CLAUDE.md?

        This is contextual - not a failure, just information.
        """
        import os

        # Check if there are references to CLAUDE.md code in tests or examples
        found_references = 0

        for root, dirs, files in os.walk("tests"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        if "CLAUDE.md" in content or "from CLAUDE" in content:
                            found_references += 1

        print(f"\nDocumentation Impact: Found {found_references} test files "
              "referencing CLAUDE.md examples")

        if found_references == 0:
            print("[WARN] Note: No test coverage for CLAUDE.md examples found. "
                  "This may explain why issues weren't caught.")

    def test_are_documentation_examples_validated_in_ci(self):
        """
        Check: Is there CI validation for code examples in docs?
        """
        import os

        # Look for doctest or similar validation
        ci_files = [".github/workflows/ci.yml", "pytest.ini", "pyproject.toml"]

        found_validation = False
        for ci_file in ci_files:
            if os.path.exists(ci_file):
                with open(ci_file, encoding="utf-8") as f:
                    content = f.read()
                    if "doctest" in content or "markdown" in content or "example" in content:
                        found_validation = True
                        print(f"[PASS] Found documentation validation in {ci_file}")

        if not found_validation:
            print("[WARN] Warning: No CI validation found for documentation examples. "
                  "This explains why these issues weren't caught automatically.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
