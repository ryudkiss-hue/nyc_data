from unittest.mock import patch

from socrata_toolkit.core import SocrataClient, SocrataConfig

class DummyResp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

@patch("socrata_toolkit.core.client.requests.get")
def test_search_maps_results(mock_get):
    mock_get.return_value = DummyResp(
        {
            "results": [
                {
                    "resource": {"id": "abcd-1234", "name": "X", "description": "D", "tags": []},
                    "metadata": {"domain": "data.city"},
                }
            ]
        }
    )
    c = SocrataClient(SocrataConfig())
    out = c.search(query="x")
    assert out[0].fourfour == "abcd-1234"
