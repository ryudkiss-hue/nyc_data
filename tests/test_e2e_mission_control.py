from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.analytics import profile_dataset
from app.data_loader import IngestionProviderFactory
from app.services.workflow_service import WorkflowOrchestrator
from socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository


@pytest.fixture
def e2e_db(tmp_path):
    db_path = str(tmp_path / "e2e.duckdb")
    # Inject into global state
    import app.data_loader

    original_path = app.data_loader._DUCKDB_PATH
    app.data_loader._DUCKDB_PATH = db_path

    # Disable L2 disk caches so we hit the mock
    original_disk = getattr(app.data_loader, "_DISK_CACHE_AVAILABLE", False)
    app.data_loader._DISK_CACHE_AVAILABLE = False

    yield db_path
    app.data_loader._DUCKDB_PATH = original_path
    app.data_loader._DISK_CACHE_AVAILABLE = original_disk


def test_full_ingestion_to_orchestration_cycle(e2e_db, mocker):
    """End-to-End smoke test for the complete Mission Control lifecycle."""
    # 1. Mock SODA3 API and legacy cache
    mock_client = MagicMock()
    mocker.patch("app.data_loader.get_socrata_client", return_value=mock_client)
    mocker.patch("app.data_loader._read_parquet_cache", return_value=None)
    mocker.patch("app.data_loader._get_duckdb_watermark", return_value=(None, None))

    # Payload for 'lot_info'
    raw_data = [
        {"bbl": "1234567890", "boro": "MN", "block": "100", "lot": "1"},
        {"bbl": "1234567891", "boro": "MN", "block": "101", "lot": "2"},
    ]
    mock_client.get.return_value = raw_data

    # 2. Step: Ingestion via Factory
    factory = IngestionProviderFactory()
    fetcher = factory.get_fetcher(mode="live")
    df_live = fetcher.fetch("lot_info", limit=10)

    assert len(df_live) == 2
    assert "_bbl" in df_live.columns  # Post-processing applied

    # 3. Step: Persistence in DuckDB
    mgr = DuckDBManager(e2e_db)
    repo = DuckDBRepository(mgr, "lot_info")
    repo.upsert_dataframe(df_live, "bbl")
    assert repo.count() == 2

    # 4. Step: Profiling using DuckDB Pushdown
    # We'll pass df_live but it should hit the DB for cardinality
    profile = profile_dataset("lot_info", df_live)
    assert profile.row_count == 2
    # Find bbl column
    bbl_col = next(c for c in profile.columns if c.name == "bbl")
    assert bbl_col.cardinality == 2

    # 5. Step: Workflow Orchestration
    # We'll provide a bundle with the ingested data
    bundle = {"lot_info": df_live, "mappluto": df_live}
    orchestrator = WorkflowOrchestrator()

    # We mock the specific complex functions to verify they receive the bundle
    with patch("app.services.workflow_service.qa_qc_inventory_ledger") as mock_qa:
        mock_qa.return_value = (pd.DataFrame(), pd.DataFrame(), 1, [])
        results = orchestrator.run_all(bundle)

        assert "qa" in results
        assert mock_qa.called
        # Verify it received our ingested data
        args, kwargs = mock_qa.call_args
        assert args[0].equals(df_live)

    mgr.close()
