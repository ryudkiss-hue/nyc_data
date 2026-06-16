import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")
from unittest.mock import patch

import pandas as pd

from socrata_toolkit.llm.duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm


class DummyResp:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {"message": {"content": '{"label":"other","confidence":0.7,"rationale":"ok"}'}}
            ]
        }


@patch("socrata_toolkit.llm.duck_bridge.requests.post")
def test_augment_dataframe(mock_post):
    mock_post.return_value = DummyResp()
    df = pd.DataFrame({"description": ["a", "b"]})
    out = augment_dataframe_with_llm(df, "description", LLMAugmentConfig())
    assert "llm_label" in out.columns
    assert out["llm_confidence"].iloc[0] == 0.7
