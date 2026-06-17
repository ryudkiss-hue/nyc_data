
from socrata_toolkit.governance import (
    check_dcwp_license,
    check_parks_permit,
    validate_contractor_for_list,
)


def test_check_dcwp_license_no_api():
    res = check_dcwp_license("ABC123", api_base=None)
    assert res["valid"] is False
    assert "No DCWP API configured" in res["details"]


def test_check_parks_permit_no_api():
    res = check_parks_permit("P-1234", api_base=None)
    assert res["valid"] is False
    assert "No Parks API configured" in res["details"]


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_validate_contractor_for_list(monkeypatch):
    # Mock requests.get for DCWP and Parks
    def fake_get(url, timeout=10):
        if "licenses" in url:
            return DummyResp({"active": True})
        if "permits" in url:
            return DummyResp({"status": "APPROVED"})
        return DummyResp({})

    monkeypatch.setattr("socrata_toolkit.governance.get", fake_get)
    res = validate_contractor_for_list(
        "contractor-1",
        "LIC-1",
        dcwp_api="http://fake.dcwp",
        parks_api="http://fake.parks",
        parks_permit="P-1",
    )
    assert res["ok"] is True
    assert res["reasons"] == []
