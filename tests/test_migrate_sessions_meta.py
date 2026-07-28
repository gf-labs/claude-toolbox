import json
import os
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

    yield tmp_path, projects, data_root


def _register(tmp_path: Path, projects: Path, name: str = "alpha") -> tuple[Path, str]:
    """Create a real repo dir + its reconstructable project-key dir.

    migrate-sessions-meta enumerates via _projects.enumerate_projects, which
    reconstructs keys against real filesystem dirs — a hand-invented key like
    "my-project" would be skipped. Returns (repo_path, key); run the subprocess
    with cwd=repo_path for single scope over exactly this project.
    """
    repo = tmp_path / "work" / name
    repo.mkdir(parents=True)
    key = str(repo).replace("/", "-")
    (projects / key).mkdir()
    return repo, key


def _make_session(proj_dir: Path, uuid: str, records: list) -> Path:
    proj_dir.mkdir(parents=True, exist_ok=True)
    f = proj_dir / f"{uuid}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return f


def _run_migrate(home: Path, cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(MIGRATE)], capture_output=True,
                          text=True, env=env, cwd=str(cwd))


def test_marks_delete_me_session_as_done(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "aaaa-1111", [
        {"type": "user", "message": {"content": "hello"}},
        {"type": "custom-title", "customTitle": "my-session-delete-me"},
    ])
    _run_migrate(tmp_path, repo)
    import session_index
    assert session_index.get_status(key, "aaaa-1111") == "done"


def test_done_name_strips_delete_me(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "aaaa-2222", [
        {"type": "custom-title", "customTitle": "my-session-delete-me"},
    ])
    _run_migrate(tmp_path, repo)
    import session_index
    reg = session_index.read_registry(key)
    assert reg["aaaa-2222"]["name"] == "my-session"


def test_marks_artifact_session(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "bbbb-2222", [
        {"type": "file-history-snapshot", "data": "x"},
    ])
    _run_migrate(tmp_path, repo)
    import session_index
    assert session_index.get_status(key, "bbbb-2222") == "artifact"


def test_skips_already_indexed(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "cccc-3333", [
        {"type": "custom-title", "customTitle": "something-delete-me"},
    ])
    import session_index
    session_index.set_status(key, "cccc-3333", "keep")
    _run_migrate(tmp_path, repo)
    assert session_index.get_status(key, "cccc-3333") == "keep"


def test_active_sessions_not_indexed(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "dddd-4444", [
        {"type": "user", "message": {"content": "hello"}},
        {"type": "custom-title", "customTitle": "active-session"},
    ])
    _run_migrate(tmp_path, repo)
    import session_index
    assert session_index.get_status(key, "dddd-4444") is None


def test_output_reports_counts(fake_env):
    tmp_path, projects, data_root = fake_env
    repo, key = _register(tmp_path, projects)
    _make_session(projects / key, "eeee-5555", [
        {"type": "custom-title", "customTitle": "done-session-delete-me"},
    ])
    _make_session(projects / key, "ffff-6666", [
        {"type": "file-history-snapshot", "data": "x"},
    ])
    result = _run_migrate(tmp_path, repo)
    assert "1 done" in result.stdout
    assert "1 artifact" in result.stdout


def test_global_scope_backfills_across_projects(fake_env):
    # Two registered projects, cwd outside both -> global scope enumerates both.
    tmp_path, projects, data_root = fake_env
    repo_a, key_a = _register(tmp_path, projects, "alpha")
    repo_b, key_b = _register(tmp_path, projects, "beta")
    _make_session(projects / key_a, "aaaa-0001", [
        {"type": "custom-title", "customTitle": "done-a-delete-me"},
    ])
    _make_session(projects / key_b, "bbbb-0002", [
        {"type": "file-history-snapshot", "data": "x"},
    ])
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_migrate(tmp_path, outside)
    assert result.returncode == 0, result.stderr
    assert "1 done" in result.stdout
    assert "1 artifact" in result.stdout
    import session_index
    assert session_index.get_status(key_a, "aaaa-0001") == "done"
    assert session_index.get_status(key_b, "bbbb-0002") == "artifact"
