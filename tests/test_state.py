from socrata_toolkit.core import load_state, save_state


def test_save_and_load_state(tmp_path):
    path = str(tmp_path / "state.json")
    save_state(path, {"domain": "data.city", "last_rows": 42})
    loaded = load_state(path)
    assert loaded["domain"] == "data.city"
    assert loaded["last_rows"] == 42

def test_load_state_missing_file(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    loaded = load_state(path)
    assert loaded == {}

def test_save_state_creates_dirs(tmp_path):
    path = str(tmp_path / "nested" / "deep" / "state.json")
    save_state(path, {"key": "value"})
    loaded = load_state(path)
    assert loaded["key"] == "value"
