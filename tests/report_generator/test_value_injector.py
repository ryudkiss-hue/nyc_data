"""
Test suite for value injection system.

Validates that dynamic values are correctly injected into templates.
"""

from datetime import date, datetime

import pytest

from app.report_generator.value_injector import (
    ValueInjectionError,
    ValueInjector,
    create_injector,
    inject_into_template,
)


class TestValueInjectorBasic:
    """Test basic value injection functionality."""

    def test_simple_string_injection(self):
        """Test simple string value injection."""
        values = {"name": "NYC", "department": "DOT"}
        template = "{name} {department} Report"
        result = inject_into_template(template, values)
        assert result == "NYC DOT Report"

    def test_numeric_injection(self):
        """Test numeric value injection."""
        values = {"count": 5823, "percentage": 0.85}
        template = "Analyzed {count} locations with {percentage} accuracy"
        result = inject_into_template(template, values)
        assert "5823" in result
        assert "0.85" in result

    def test_boolean_injection(self):
        """Test boolean value injection."""
        values = {"is_valid": True, "is_complete": False}
        template = "Valid: {is_valid}, Complete: {is_complete}"
        result = inject_into_template(template, values)
        assert "Yes" in result
        assert "No" in result

    def test_date_injection(self):
        """Test date value injection."""
        test_date = date(2026, 6, 11)
        values = {"date": test_date}
        template = "Report Date: {date}"
        result = inject_into_template(template, values)
        assert "2026-06-11" in result

    def test_list_injection(self):
        """Test list value injection (converts to comma-separated)."""
        values = {"boroughs": ["Manhattan", "Brooklyn", "Bronx"]}
        template = "Boroughs: {boroughs}"
        result = inject_into_template(template, values)
        assert "Manhattan, Brooklyn, Bronx" in result

    def test_none_value_injection(self):
        """Test that None values are converted to 'N/A'."""
        values = {"missing_value": None}
        template = "Value: {missing_value}"
        result = inject_into_template(template, values)
        assert "N/A" in result


class TestFormatSpecifiers:
    """Test format specifier handling."""

    def test_float_format_specifier(self):
        """Test float format specifier (e.g., .2f)."""
        values = {"value": 0.34567}
        template = "Moran's I = {value:.3f}"
        result = inject_into_template(template, values)
        assert "0.346" in result

    def test_integer_format_specifier(self):
        """Test integer format specifier."""
        values = {"count": 5823}
        template = "Count: {count:,d}"
        result = inject_into_template(template, values)
        assert "5,823" in result

    def test_percent_format_specifier(self):
        """Test percent format specifier."""
        values = {"rate": 0.85}
        template = "Rate: {rate:.1%}"
        result = inject_into_template(template, values)
        assert "85.0%" in result

    def test_multiple_format_specifiers(self):
        """Test multiple format specifiers in same template."""
        values = {"morans_i": 0.34567, "p_value": 0.00234, "count": 5823}
        template = "Moran's I = {morans_i:.3f}, p-value = {p_value:.4f}, Count = {count:,d}"
        result = inject_into_template(template, values)
        assert "0.346" in result
        assert "0.0023" in result
        assert "5,823" in result


class TestErrorHandling:
    """Test error conditions and edge cases."""

    def test_missing_placeholder_raises_error(self):
        """Test that missing placeholder raises ValueInjectionError."""
        values = {"name": "NYC"}
        template = "{name} {missing_field}"
        with pytest.raises(ValueInjectionError):
            inject_into_template(template, values)

    def test_invalid_format_specifier_raises_error(self):
        """Test that invalid format specifier raises error."""
        values = {"value": "not_a_number"}
        template = "{value:.2f}"
        with pytest.raises(ValueInjectionError):
            inject_into_template(template, values)

    def test_empty_values_dict_raises_error(self):
        """Test that empty values dict raises error."""
        with pytest.raises(ValueInjectionError):
            ValueInjector({})

    def test_no_placeholders_in_template(self):
        """Test template with no placeholders."""
        values = {"unused": "value"}
        template = "This is a plain template"
        result = inject_into_template(template, values)
        assert result == template


class TestValueInjectorClass:
    """Test ValueInjector class methods."""

    def test_create_injector_factory(self):
        """Test create_injector factory function."""
        values = {"test": "value"}
        injector = create_injector(values)
        assert isinstance(injector, ValueInjector)

    def test_get_value_method(self):
        """Test get_value method for safe access."""
        values = {"existing": "value"}
        injector = ValueInjector(values)

        assert injector.get_value("existing") == "value"
        assert injector.get_value("missing") is None
        assert injector.get_value("missing", "default") == "default"

    def test_multiple_injections_same_injector(self):
        """Test using same injector for multiple templates."""
        values = {"count": 100, "name": "Test"}
        injector = ValueInjector(values)

        template1 = "{name}: {count}"
        template2 = "Total {name} items: {count:,d}"

        result1 = injector.inject(template1)
        result2 = injector.inject(template2)

        assert "Test: 100" in result1
        assert "Total Test items: 100" in result2

    def test_value_normalization(self):
        """Test that values are normalized correctly."""
        values = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "date": date(2026, 6, 11),
            "list": [1, 2, 3],
            "none": None,
        }
        injector = ValueInjector(values)

        # All should have non-None values in normalized dict
        assert injector.values["string"] == "test"
        assert injector.values["int"] == 42
        assert injector.values["float"] == 3.14
        assert injector.values["bool_true"] == "Yes"
        assert injector.values["bool_false"] == "No"
        assert injector.values["date"] == "2026-06-11"
        assert "1" in injector.values["list"]
        assert injector.values["none"] == "N/A"


class TestReportIntegration:
    """Test value injection in realistic report scenarios."""

    def test_morans_i_report_values(self):
        """Test injection of Moran's I report values."""
        values = {
            "report_date": date(2026, 6, 11),
            "morans_i_value": 0.34567,
            "p_value": 0.00234,
            "location_count": 5823,
            "borough_list": ["Manhattan", "Brooklyn", "Bronx"],
            "confidence_level": "95%",
        }

        template = (
            "Report: {report_date}\n"
            "Moran's I = {morans_i_value:.3f}\n"
            "p-value = {p_value:.4f}\n"
            "Locations: {location_count:,d}\n"
            "Boroughs: {borough_list}\n"
            "Confidence: {confidence_level}"
        )

        result = inject_into_template(template, values)

        assert "2026-06-11" in result
        assert "0.346" in result
        assert "0.0023" in result
        assert "5,823" in result
        assert "Manhattan, Brooklyn, Bronx" in result
        assert "95%" in result

    def test_distribution_report_values(self):
        """Test injection of distribution report values."""
        values = {
            "distribution_type": "RIGHT_SKEWED",
            "skewness": 0.85,
            "kurtosis": 4.2,
            "concentration_pct": 67.5,
            "valid_count": 450,
            "record_count": 500,
            "validity_percentage": 90.0,
        }

        template = (
            "Distribution: {distribution_type}\n"
            "Skewness: {skewness:.2f}\n"
            "Kurtosis: {kurtosis:.2f}\n"
            "Concentration: {concentration_pct:.1f}%\n"
            "Valid: {valid_count}/{record_count} ({validity_percentage:.1f}%)"
        )

        result = inject_into_template(template, values)

        assert "RIGHT_SKEWED" in result
        assert "0.85" in result
        assert "4.20" in result
        assert "67.5%" in result
        assert "450/500" in result
        assert "90.0%" in result

    def test_sla_forecast_report_values(self):
        """Test injection of SLA forecast report values."""
        values = {
            "point_estimate": 78.5,
            "sla_target": 90.0,
            "ci_lower": 72.3,
            "ci_upper": 84.7,
            "prob_meets_sla": 25.0,
            "approval_deadline": "2026-06-30",
            "total_investment": 250000,
            "expected_benefit": 180000,
            "roi_pct": 72,
        }

        template = (
            "Estimate: {point_estimate:.1f}% (Target: {sla_target:.0f}%)\n"
            "CI: [{ci_lower:.1f}%, {ci_upper:.1f}%]\n"
            "Success Probability: {prob_meets_sla:.0f}%\n"
            "Approval: {approval_deadline}\n"
            "Investment: ${total_investment:,d}\n"
            "Benefit: ${expected_benefit:,d}\n"
            "ROI: {roi_pct:.0f}%"
        )

        result = inject_into_template(template, values)

        assert "78.5%" in result
        assert "Target: 90%" in result
        assert "72.3%" in result
        assert "84.7%" in result
        assert "25%" in result
        assert "2026-06-30" in result
        assert "$250,000" in result
        assert "$180,000" in result
        assert "72%" in result
