from unittest.mock import patch

from app.services.nl_query import parse_complaint_to_json, triage_complaint


@patch("app.services.nl_query._call_llm")
def test_parse_complaint_to_json(mock_call_llm):
    mock_call_llm.return_value = {
        "severity": "high",
        "category": "street-condition",
        "summary": "Large pothole on Broadway",
    }

    result = parse_complaint_to_json("There is a large pothole on Broadway!")

    assert result["severity"] == "high"
    assert result["category"] == "street-condition"
    assert "pothole" in result["summary"]
    mock_call_llm.assert_called_once()


@patch("app.services.nl_query._call_llm")
def test_triage_complaint(mock_call_llm):
    mock_call_llm.return_value = {
        "frustration_score": 9,
        "escalate": True,
        "reason": "Repeated complaints ignored",
    }

    result = triage_complaint("I have complained 5 times and nothing happened!")

    assert result["frustration_score"] == 9
    assert result["escalate"] is True
    mock_call_llm.assert_called_once()
