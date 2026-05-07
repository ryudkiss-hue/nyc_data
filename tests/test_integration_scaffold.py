import os

import pytest


@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Set RUN_INTEGRATION=1 to enable integration tests")
def test_integration_environment_ready():
    assert os.getenv("PG_DSN")
    assert os.getenv("MONGO_URI")
