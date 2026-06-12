from pathlib import Path

from socrata_toolkit.core import get_default, load_local_config

def test_get_default_nested():
    cfg = {"a": {"b": 2}}
    assert get_default(cfg, "a", "b", default=0) == 2
    assert get_default(cfg, "x", default=9) == 9

def test_load_local_config(tmp_path: Path):
    p = tmp_path / "socrata_toolkit.core"
    p.write_text('{"preferences": {"default_max_rows": 12}}', encoding="utf-8")
    cfg = load_local_config(str(p))
    assert cfg["preferences"]["default_max_rows"] == 12
