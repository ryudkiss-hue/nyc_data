"""Tests for governance.compliance module - License and permit validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from socrata_toolkit.governance.compliance import (
    check_dcwp_license,
    check_parks_permit,
    validate_contractor_for_list,
)


class TestCheckDCWPLicense:
    """Tests for check_dcwp_license function."""

    def test_check_dcwp_license_no_api(self):
        """Test with no API configured."""
        result = check_dcwp_license("LIC123")
        assert result["valid"] is False
        assert "No DCWP API configured" in result["details"]

    def test_check_dcwp_license_with_api_none(self):
        """Test explicitly passing None for api_base."""
        result = check_dcwp_license("LIC456", api_base=None)
        assert result["valid"] is False
        assert "No DCWP API configured" in result["details"]

    def test_check_dcwp_license_success(self):
        """Test successful license check."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"active": True, "name": "ABC Contractors"}
            mock_get.return_value = mock_response

            result = check_dcwp_license("LIC789", api_base="https://api.dcwp.gov")
            assert result["valid"] is True
            assert result["details"]["active"] is True
            mock_get.assert_called_once_with(
                "https://api.dcwp.gov/licenses/LIC789",
                timeout=10,
            )

    def test_check_dcwp_license_inactive(self):
        """Test with inactive license."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"active": False, "name": "Inactive Co"}
            mock_get.return_value = mock_response

            result = check_dcwp_license("LIC999", api_base="https://api.dcwp.gov")
            assert result["valid"] is False

    def test_check_dcwp_license_http_error(self):
        """Test HTTP error handling."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_get.side_effect = Exception("Connection timeout")

            result = check_dcwp_license("LIC000", api_base="https://api.dcwp.gov")
            assert result["valid"] is False
            assert "Connection timeout" in result["details"]

    def test_check_dcwp_license_http_status_error(self):
        """Test HTTP status error."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("404 Not Found")
            mock_get.return_value = mock_response

            result = check_dcwp_license("INVALID", api_base="https://api.dcwp.gov")
            assert result["valid"] is False
            assert "404 Not Found" in result["details"]

    def test_check_dcwp_license_missing_active_field(self):
        """Test with missing 'active' field in response."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"name": "Test Contractor"}
            mock_get.return_value = mock_response

            result = check_dcwp_license("LIC111", api_base="https://api.dcwp.gov")
            # Should default to False when 'active' is missing
            assert result["valid"] is False

    def test_check_dcwp_license_url_construction(self):
        """Test that URL is constructed correctly."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"active": True}
            mock_get.return_value = mock_response

            check_dcwp_license("TEST-LIC-123", api_base="https://example.com/api")
            mock_get.assert_called_once_with(
                "https://example.com/api/licenses/TEST-LIC-123",
                timeout=10,
            )


class TestCheckParkspermit:
    """Tests for check_parks_permit function."""

    def test_check_parks_permit_no_api(self):
        """Test with no API configured."""
        result = check_parks_permit("PERMIT123")
        assert result["valid"] is False
        assert "No Parks API configured" in result["details"]

    def test_check_parks_permit_with_api_none(self):
        """Test explicitly passing None for api_base."""
        result = check_parks_permit("PERMIT456", api_base=None)
        assert result["valid"] is False
        assert "No Parks API configured" in result["details"]

    def test_check_parks_permit_approved(self):
        """Test approved permit."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "APPROVED", "area": "Central Park"}
            mock_get.return_value = mock_response

            result = check_parks_permit("PERMIT789", api_base="https://api.parks.gov")
            assert result["valid"] is True
            assert result["details"]["status"] == "APPROVED"

    def test_check_parks_permit_rejected(self):
        """Test rejected permit."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "REJECTED"}
            mock_get.return_value = mock_response

            result = check_parks_permit("PERMIT999", api_base="https://api.parks.gov")
            assert result["valid"] is False

    def test_check_parks_permit_pending(self):
        """Test pending permit status."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "PENDING"}
            mock_get.return_value = mock_response

            result = check_parks_permit("PERMIT111", api_base="https://api.parks.gov")
            assert result["valid"] is False  # Only APPROVED is valid

    def test_check_parks_permit_http_error(self):
        """Test HTTP error handling."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = check_parks_permit("PERMIT000", api_base="https://api.parks.gov")
            assert result["valid"] is False
            assert "Network error" in result["details"]

    def test_check_parks_permit_missing_status_field(self):
        """Test with missing 'status' field."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"area": "Some Park"}
            mock_get.return_value = mock_response

            result = check_parks_permit("PERMIT222", api_base="https://api.parks.gov")
            # Should be False when status != APPROVED
            assert result["valid"] is False

    def test_check_parks_permit_url_construction(self):
        """Test that URL is constructed correctly."""
        with patch("socrata_toolkit.governance.compliance._http_get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "APPROVED"}
            mock_get.return_value = mock_response

            check_parks_permit("PERM-2024-001", api_base="https://example.com/parks")
            mock_get.assert_called_once_with(
                "https://example.com/parks/permits/PERM-2024-001",
                timeout=10,
            )


class TestValidateContractorForList:
    """Tests for validate_contractor_for_list function."""

    def test_validate_contractor_valid_license_no_permit(self):
        """Test valid contractor without permit requirement."""
        with patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic:
            mock_lic.return_value = {"valid": True, "details": {}}

            result = validate_contractor_for_list(
                "CONT123",
                "LIC123",
                dcwp_api="https://api.dcwp.gov",
            )
            assert result["ok"] is True
            assert len(result["reasons"]) == 0

    def test_validate_contractor_invalid_license(self):
        """Test invalid license."""
        with patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic:
            mock_lic.return_value = {
                "valid": False,
                "details": "License not found",
            }

            result = validate_contractor_for_list(
                "CONT456",
                "INVALID_LIC",
                dcwp_api="https://api.dcwp.gov",
            )
            assert result["ok"] is False
            assert any("DCWP license invalid" in r for r in result["reasons"])

    def test_validate_contractor_valid_license_valid_permit(self):
        """Test valid license and valid permit."""
        with (
            patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic,
            patch("socrata_toolkit.governance.compliance.check_parks_permit") as mock_permit,
        ):
            mock_lic.return_value = {"valid": True, "details": {}}
            mock_permit.return_value = {"valid": True, "details": {}}

            result = validate_contractor_for_list(
                "CONT789",
                "LIC789",
                dcwp_api="https://api.dcwp.gov",
                parks_api="https://api.parks.gov",
                parks_permit="PERMIT789",
            )
            assert result["ok"] is True
            assert len(result["reasons"]) == 0

    def test_validate_contractor_valid_license_invalid_permit(self):
        """Test valid license but invalid permit."""
        with (
            patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic,
            patch("socrata_toolkit.governance.compliance.check_parks_permit") as mock_permit,
        ):
            mock_lic.return_value = {"valid": True, "details": {}}
            mock_permit.return_value = {"valid": False, "details": "Permit rejected"}

            result = validate_contractor_for_list(
                "CONT999",
                "LIC999",
                dcwp_api="https://api.dcwp.gov",
                parks_api="https://api.parks.gov",
                parks_permit="PERMIT999",
            )
            assert result["ok"] is False
            assert any("Parks permit invalid" in r for r in result["reasons"])

    def test_validate_contractor_both_invalid(self):
        """Test both license and permit invalid."""
        with (
            patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic,
            patch("socrata_toolkit.governance.compliance.check_parks_permit") as mock_permit,
        ):
            mock_lic.return_value = {"valid": False, "details": "Inactive"}
            mock_permit.return_value = {"valid": False, "details": "Pending"}

            result = validate_contractor_for_list(
                "CONT000",
                "LIC000",
                dcwp_api="https://api.dcwp.gov",
                parks_api="https://api.parks.gov",
                parks_permit="PERMIT000",
            )
            assert result["ok"] is False
            assert len(result["reasons"]) == 2

    def test_validate_contractor_no_permit_check(self):
        """Test with valid license and no permit to check."""
        with patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic:
            mock_lic.return_value = {"valid": True, "details": {}}

            result = validate_contractor_for_list(
                "CONT111",
                "LIC111",
                dcwp_api="https://api.dcwp.gov",
                parks_api=None,
                parks_permit=None,
            )
            assert result["ok"] is True

    def test_validate_contractor_license_details_in_reasons(self):
        """Test that license details appear in reasons."""
        with patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic:
            mock_lic.return_value = {
                "valid": False,
                "details": "License expired on 2023-12-31",
            }

            result = validate_contractor_for_list(
                "CONT222",
                "EXPIRED_LIC",
                dcwp_api="https://api.dcwp.gov",
            )
            assert "License expired on 2023-12-31" in result["reasons"][0]

    def test_validate_contractor_permit_details_in_reasons(self):
        """Test that permit details appear in reasons."""
        with (
            patch("socrata_toolkit.governance.compliance.check_dcwp_license") as mock_lic,
            patch("socrata_toolkit.governance.compliance.check_parks_permit") as mock_permit,
        ):
            mock_lic.return_value = {"valid": True, "details": {}}
            mock_permit.return_value = {
                "valid": False,
                "details": "Permit withdrawn",
            }

            result = validate_contractor_for_list(
                "CONT333",
                "LIC333",
                dcwp_api="https://api.dcwp.gov",
                parks_api="https://api.parks.gov",
                parks_permit="PERMIT333",
            )
            assert "Permit withdrawn" in result["reasons"][0]
