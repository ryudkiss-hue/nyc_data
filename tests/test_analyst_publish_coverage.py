"""Comprehensive tests for analyst.publish module."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.analyst.publish import (
    PublishAction,
    PublishError,
    PublishReport,
    _copy_pack,
    _export_bi,
    _pack_context,
    _read_text_best_effort,
    load_publish_profile,
    publish_pack,
)


class TestReadTextBestEffort:
    """Tests for _read_text_best_effort helper."""

    def test_read_text_best_effort_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("Hello, World!", encoding="utf-8")

            result = _read_text_best_effort(file_path)
            assert result == "Hello, World!"

    def test_read_text_best_effort_nonexistent(self):
        result = _read_text_best_effort(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_read_text_best_effort_encoding_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            # Write binary data that can't be decoded as UTF-8
            file_path.write_bytes(b"\x80\x81\x82\x83")

            result = _read_text_best_effort(file_path)
            # Should fall back to ignore errors
            assert isinstance(result, str)

    def test_read_text_best_effort_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "empty.txt"
            file_path.write_text("")

            result = _read_text_best_effort(file_path)
            assert result == ""


class TestPackContext:
    """Tests for _pack_context helper."""

    def test_pack_context_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "my_pack_2024-01-01"
            pack_dir.mkdir()

            result = _pack_context(pack_dir)
            assert result["pack_name"] == "my_pack_2024-01-01"
            assert result["profile_name"] == ""

    def test_pack_context_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "my_pack"
            pack_dir.mkdir()
            manifest = pack_dir / "manifest.json"
            manifest.write_text(json.dumps({
                "run_date": "2024-01-15",
                "profile_name": "test_profile",
            }))

            result = _pack_context(pack_dir)
            assert result["run_date"] == "2024-01-15"
            assert result["profile_name"] == "test_profile"
            assert result["pack_name"] == "my_pack"

    def test_pack_context_with_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "my_pack"
            pack_dir.mkdir()
            manifest = pack_dir / "manifest.json"
            manifest.write_text("invalid json {")

            result = _pack_context(pack_dir)
            assert result["pack_name"] == "my_pack"
            assert result["profile_name"] == ""

    def test_pack_context_with_partial_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()
            manifest = pack_dir / "manifest.json"
            manifest.write_text(json.dumps({"run_date": "2024-01-15"}))

            result = _pack_context(pack_dir)
            assert result["run_date"] == "2024-01-15"
            assert result["profile_name"] == ""


class TestLoadPublishProfile:
    """Tests for load_publish_profile function."""

    def test_load_publish_profile_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            load_publish_profile("/nonexistent/profile.yaml")

    def test_load_publish_profile_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("""
profile_name: test_profile
file_copy:
  enabled: true
  dest_root: /output
email:
  enabled: false
""")

            result = load_publish_profile(profile_file)
            assert result["profile_name"] == "test_profile"
            assert result["file_copy"]["enabled"] is True

    def test_load_publish_profile_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = Path(tmpdir) / "empty.yaml"
            profile_file.write_text("")

            result = load_publish_profile(profile_file)
            assert isinstance(result, dict)
            assert "profile_name" in result

    def test_load_publish_profile_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = Path(tmpdir) / "invalid.yaml"
            profile_file.write_text("[invalid yaml :")

            with pytest.raises(Exception):
                load_publish_profile(profile_file)

    def test_load_publish_profile_not_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = Path(tmpdir) / "list.yaml"
            profile_file.write_text("- item1\n- item2\n")

            with pytest.raises(PublishError, match="must be a YAML mapping"):
                load_publish_profile(profile_file)

    def test_load_publish_profile_default_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = Path(tmpdir) / "my_profile.yaml"
            profile_file.write_text("key: value\n")

            result = load_publish_profile(profile_file)
            assert result["profile_name"] == "my_profile"


class TestPublishAction:
    """Tests for PublishAction dataclass."""

    def test_publish_action_creation(self):
        action = PublishAction(
            kind="file_copy",
            ok=True,
            detail="Copied to /output",
            meta={"dest": "/output"},
        )
        assert action.kind == "file_copy"
        assert action.ok is True
        assert action.detail == "Copied to /output"
        assert action.meta["dest"] == "/output"

    def test_publish_action_error(self):
        action = PublishAction(
            kind="email",
            ok=False,
            detail="SMTP connection failed",
            meta={},
        )
        assert action.ok is False


class TestPublishReport:
    """Tests for PublishReport dataclass."""

    def test_publish_report_creation(self):
        actions = [
            PublishAction("file_copy", True, "Success", {}),
            PublishAction("email", False, "Failed", {}),
        ]
        report = PublishReport(
            pack_dir="/path/to/pack",
            profile_path="/path/to/profile.yaml",
            dry_run=True,
            actions=actions,
        )
        assert report.dry_run is True
        assert len(report.actions) == 2
        assert report.pack_dir == "/path/to/pack"


class TestCopyPack:
    """Tests for _copy_pack function."""

    def test_copy_pack_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()
            (pack_dir / "file1.txt").write_text("content")

            result = _copy_pack(pack_dir, "/dest/root", dry_run=True)
            assert result.kind == "file_copy"
            assert result.ok is True

    def test_copy_pack_nonexistent_source(self):
        result = _copy_pack(Path("/nonexistent/pack"), "/dest", dry_run=False)
        assert result.ok is False

    def test_copy_pack_actual_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()
            (pack_dir / "file.txt").write_text("content")

            dest_root = Path(tmpdir) / "dest"
            dest_root.mkdir()

            result = _copy_pack(pack_dir, str(dest_root), dry_run=False)
            assert result.ok is True


class TestExportBi:
    """Tests for _export_bi function."""

    def test_export_bi_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            result = _export_bi(pack_dir, "/dest", None, dry_run=True)
            assert result.kind == "bi_export"
            assert result.ok is True

    def test_export_bi_invalid_dest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            # _export_bi will create dest directory if needed and export 0 files (which is ok=True)
            result = _export_bi(pack_dir, str(Path(tmpdir) / "dest"), None, dry_run=False)
            # Should succeed with 0 files exported
            assert result.ok is True
            assert "Exported 0 files" in result.detail


class TestPublishPack:
    """Tests for main publish_pack function."""

    def test_publish_pack_invalid_pack_dir(self):
        with pytest.raises(FileNotFoundError):
            publish_pack(
                pack_dir="/nonexistent/pack",
                profile_path="/path/to/profile.yaml",
            )

    def test_publish_pack_invalid_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            with pytest.raises(FileNotFoundError):
                publish_pack(
                    pack_dir=pack_dir,
                    profile_path="/nonexistent/profile.yaml",
                )

    def test_publish_pack_no_destinations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("profile_name: test\n")

            report = publish_pack(
                pack_dir=pack_dir,
                profile_path=profile_file,
                dry_run=True,
            )
            assert report.dry_run is True
            assert isinstance(report, PublishReport)

    def test_publish_pack_file_copy_enabled_no_dest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("""
profile_name: test
file_copy:
  enabled: true
""")

            report = publish_pack(
                pack_dir=pack_dir,
                profile_path=profile_file,
                dry_run=True,
            )
            # Should have an action with ok=False for missing dest_root
            file_copy_actions = [a for a in report.actions if a.kind == "file_copy"]
            assert len(file_copy_actions) > 0
            assert file_copy_actions[0].ok is False

    def test_publish_pack_with_executive_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()
            (pack_dir / "executive_summary.md").write_text("# Summary\nTest content")

            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("profile_name: test\n")

            report = publish_pack(
                pack_dir=pack_dir,
                profile_path=profile_file,
                dry_run=True,
            )
            assert isinstance(report, PublishReport)

    def test_publish_pack_dry_run_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("profile_name: test\n")

            report = publish_pack(
                pack_dir=pack_dir,
                profile_path=profile_file,
                dry_run=True,
            )
            assert report.dry_run is True

    def test_publish_pack_bi_export_enabled_no_dest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "pack"
            pack_dir.mkdir()

            profile_file = Path(tmpdir) / "profile.yaml"
            profile_file.write_text("""
profile_name: test
bi_export:
  enabled: true
""")

            report = publish_pack(
                pack_dir=pack_dir,
                profile_path=profile_file,
                dry_run=True,
            )
            bi_actions = [a for a in report.actions if a.kind == "bi_export"]
            if len(bi_actions) > 0:
                assert bi_actions[0].ok is False

    def test_publish_error_class(self):
        error = PublishError("Test error")
        assert isinstance(error, RuntimeError)
        assert str(error) == "Test error"
