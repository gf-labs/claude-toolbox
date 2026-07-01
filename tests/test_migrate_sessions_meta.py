import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
MIGRATE = SCRIPTS / "migrate-sessions-meta.py"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def fake_env(tmp_path, monkeypatch):
    projects = tmp_path / ".claude" / "projects"
    projects.mkdir(parents=True)
    data_root = tmp_path / ".claude" / "data" / "tools"
    data_root.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(tmp_path))

    import session_index
    monkeypatch.setattr(session_index, "DATA_ROOT", data_root)

    yield projects, data_root


def _make_session(proj_dir: Path, uuid: str, records: list) -> Path:
    proj_dir.mkdir(parents=True, exist_ok=True)
    f = proj_dir / f"{uuid}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return f


def _run_migrate(home: Path) -> subprocess.CompletedProcess:
    env = {**__import__("os").environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(MIGRATE)], capture_output=True, text=True, env=env)


def test_marks_delete_me_session_as_done(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "aaaa-1111", [
        {"type": "user", "message": {"content": "hello"}},
        {"type": "custom-title", "customTitle": "my-session-delete-me"},
    ])
    _run_migrate(projects.parent.parent)
    import session_index
    assert session_index.get_status("my-project", "aaaa-1111") == "done"


def test_done_name_strips_delete_me(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "aaaa-2222", [
        {"type": "custom-title", "customTitle": "my-session-delete-me"},
    ])
    _run_migrate(projects.parent.parent)
    import session_index
    reg = session_index.read_registry("my-project")
    assert reg["aaaa-2222"]["name"] == "my-session"


def test_marks_artifact_session(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "bbbb-2222", [
        {"type": "file-history-snapshot", "data": "x"},
    ])
    _run_migrate(projects.parent.parent)
    import session_index
    assert session_index.get_status("my-project", "bbbb-2222") == "artifact"


def test_skips_already_indexed(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "cccc-3333", [
        {"type": "custom-title", "customTitle": "something-delete-me"},
    ])
    import session_index
    session_index.set_status("my-project", "cccc-3333", "keep")
    _run_migrate(projects.parent.parent)
    assert session_index.get_status("my-project", "cccc-3333") == "keep"


def test_active_sessions_not_indexed(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "dddd-4444", [
        {"type": "user", "message": {"content": "hello"}},
        {"type": "custom-title", "customTitle": "active-session"},
    ])
    _run_migrate(projects.parent.parent)
    import session_index
    assert session_index.get_status("my-project", "dddd-4444") is None


def test_output_reports_counts(fake_env):
    projects, data_root = fake_env
    proj = projects / "my-project"
    _make_session(proj, "eeee-5555", [
        {"type": "custom-title", "customTitle": "done-session-delete-me"},
    ])
    _make_session(proj, "ffff-6666", [
        {"type": "file-history-snapshot", "data": "x"},
    ])
    result = _run_migrate(projects.parent.parent)
    assert "1 done" in result.stdout
    assert "1 artifact" in result.stdout
