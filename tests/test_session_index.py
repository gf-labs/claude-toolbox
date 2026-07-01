import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(autouse=True)
def patch_data_root(tmp_path, monkeypatch):
    if 'session_index' in sys.modules:
        del sys.modules['session_index']
    import session_index
    monkeypatch.setattr(session_index, "DATA_ROOT", tmp_path)
    yield
    if 'session_index' in sys.modules:
        del sys.modules['session_index']


def test_read_missing_registry():
    import session_index
    assert session_index.read_registry("my-project") == {}


def test_write_and_read_round_trip():
    import session_index
    data = {"abc-123": {"status": "done", "done_at": "2026-01-01T00:00:00Z"}}
    session_index.write_registry("my-project", data)
    assert session_index.read_registry("my-project") == data


def test_get_status_absent():
    import session_index
    assert session_index.get_status("my-project", "abc-123") is None


def test_set_status_creates_entry():
    import session_index
    session_index.set_status("my-project", "abc-123", "done", done_at="2026-01-01T00:00:00Z")
    assert session_index.get_status("my-project", "abc-123") == "done"


def test_set_status_merges_kwargs():
    import session_index
    session_index.set_status("my-project", "abc-123", "done", name="my-session", done_at="2026-01-01T00:00:00Z")
    reg = session_index.read_registry("my-project")
    assert reg["abc-123"]["name"] == "my-session"
    assert reg["abc-123"]["status"] == "done"


def test_write_is_atomic():
    import session_index
    session_index.write_registry("my-project", {"x": {"status": "done"}})
    # Verify no temp files are left behind (cleanup is atomic)
    # DATA_ROOT is patched to tmp_path by the autouse fixture
    tmp_files = list(session_index.DATA_ROOT.rglob("*.tmp"))
    assert tmp_files == [], f"Temp file left behind: {tmp_files}"


def test_write_creates_parent_dirs():
    import session_index
    session_index.write_registry("deep-project", {"x": {"status": "done"}})
    expected = session_index.DATA_ROOT / "deep-project" / "sessions-meta.json"
    assert expected.exists()


def test_get_status_keep():
    import session_index
    session_index.set_status("my-project", "xyz", "keep", done_at="2026-01-01T00:00:00Z")
    assert session_index.get_status("my-project", "xyz") == "keep"


def test_set_status_overwrites_existing():
    import session_index
    session_index.set_status("my-project", "abc-123", "done", done_at="2026-01-01T00:00:00Z")
    session_index.set_status("my-project", "abc-123", "keep", done_at="2026-01-02T00:00:00Z")
    assert session_index.get_status("my-project", "abc-123") == "keep"


def test_read_corrupt_registry():
    import session_index
    path = session_index.DATA_ROOT / "my-project" / "sessions-meta.json"
    path.parent.mkdir(parents=True)
    path.write_text("{ bad json !!!")
    assert session_index.read_registry("my-project") == {}
