"""Tests for core.persistence module - Pipeline persistence layer."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from socrata_toolkit.core.persistence import (
    delete_pipeline,
    load_pipelines,
    save_pipeline,
)

class TestLoadPipelines:
    """Tests for load_pipelines function."""

    def test_load_pipelines_file_not_exists(self):
        """Test loading when store file doesn't exist."""
        with patch("socrata_toolkit.core.persistence._STORE") as mock_store:
            mock_store.exists.return_value = False
            result = load_pipelines()
            assert result == {}

    def test_load_pipelines_valid_json(self):
        """Test loading valid JSON from store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"
            test_data = {"pipeline1": {"name": "test"}, "pipeline2": {"name": "test2"}}
            store_path.write_text(json.dumps(test_data), encoding="utf-8")

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                result = load_pipelines()
                assert result == test_data

    def test_load_pipelines_empty_json(self):
        """Test loading empty JSON object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"
            store_path.write_text("{}", encoding="utf-8")

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                result = load_pipelines()
                assert result == {}

    def test_load_pipelines_malformed_json(self):
        """Test loading malformed JSON returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"
            store_path.write_text("{ invalid json }", encoding="utf-8")

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                result = load_pipelines()
                assert result == {}

    def test_load_pipelines_read_error(self):
        """Test handling of read errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"
            store_path.write_text('{"valid": "json"}', encoding="utf-8")

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                with patch.object(Path, "read_text", side_effect=OSError("Read error")):
                    result = load_pipelines()
                    assert result == {}

class TestSavePipeline:
    """Tests for save_pipeline function."""

    def test_save_pipeline_new(self):
        """Test saving a new pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                config = {"steps": [{"name": "step1"}]}
                save_pipeline("test_pipeline", config)

                assert store_path.exists()
                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert "test_pipeline" in loaded
                assert loaded["test_pipeline"] == config

    def test_save_pipeline_multiple(self):
        """Test saving multiple pipelines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                config1 = {"steps": [{"name": "step1"}]}
                config2 = {"steps": [{"name": "step2"}]}

                save_pipeline("pipeline1", config1)
                save_pipeline("pipeline2", config2)

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert len(loaded) == 2
                assert loaded["pipeline1"] == config1
                assert loaded["pipeline2"] == config2

    def test_save_pipeline_overwrite(self):
        """Test overwriting existing pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                config1 = {"version": 1}
                config2 = {"version": 2}

                save_pipeline("pipeline", config1)
                save_pipeline("pipeline", config2)

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert loaded["pipeline"]["version"] == 2

    def test_save_pipeline_preserves_others(self):
        """Test that saving one pipeline preserves others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("existing", {"data": "old"})
                save_pipeline("new", {"data": "new"})

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert "existing" in loaded
                assert "new" in loaded
                assert loaded["existing"]["data"] == "old"

    def test_save_pipeline_complex_config(self):
        """Test saving pipeline with complex nested config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                config = {
                    "name": "complex",
                    "steps": [
                        {"type": "fetch", "dataset": "violations", "params": {"limit": 1000}},
                        {"type": "transform", "rules": ["rule1", "rule2"]},
                    ],
                    "metadata": {"author": "test", "version": 1.0},
                }
                save_pipeline("complex_pipeline", config)

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert loaded["complex_pipeline"] == config

class TestDeletePipeline:
    """Tests for delete_pipeline function."""

    def test_delete_pipeline_exists(self):
        """Test deleting an existing pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("to_delete", {"data": "test"})
                save_pipeline("to_keep", {"data": "keep"})

                delete_pipeline("to_delete")

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert "to_delete" not in loaded
                assert "to_keep" in loaded

    def test_delete_pipeline_not_exists(self):
        """Test deleting non-existent pipeline does nothing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("existing", {"data": "test"})
                delete_pipeline("nonexistent")

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert "existing" in loaded
                assert len(loaded) == 1

    def test_delete_pipeline_last_one(self):
        """Test deleting the last pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("only", {"data": "test"})
                delete_pipeline("only")

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert len(loaded) == 0

    def test_delete_pipeline_multiple(self):
        """Test deleting multiple pipelines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("p1", {"data": "1"})
                save_pipeline("p2", {"data": "2"})
                save_pipeline("p3", {"data": "3"})

                delete_pipeline("p1")
                delete_pipeline("p3")

                loaded = json.loads(store_path.read_text(encoding="utf-8"))
                assert list(loaded.keys()) == ["p2"]

    def test_delete_pipeline_json_formatting(self):
        """Test that deleted pipeline's JSON is still valid and formatted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "pipelines.json"

            with patch("socrata_toolkit.core.persistence._STORE", store_path):
                save_pipeline("p1", {"data": "1"})
                save_pipeline("p2", {"data": "2"})

                delete_pipeline("p1")

                content = store_path.read_text(encoding="utf-8")
                loaded = json.loads(content)
                assert loaded == {"p2": {"data": "2"}}
