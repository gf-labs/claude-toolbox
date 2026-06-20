"""Tests for _scope — project-key reconstruction and scope detection.

_reconstruct is the subtle one: project keys join path components with '-',
but directory names may themselves contain '-', so decoding a key back to a
path is ambiguous. The function backtracks over every '/'-vs-'-' split and
yields each interpretation that actually exists on disk.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _scope  # noqa: E402


def _key(path: Path) -> str:
    return str(path).replace("/", "-")


# --------------------------------------------------------------------------
# _reconstruct
# --------------------------------------------------------------------------

def test_reconstruct_resolves_hyphenated_dir(tmp_path):
    # only ".../Repos/my-project" exists, so the final '-' must be read as a
    # literal hyphen, not a path separator.
    proj = tmp_path / "Repos" / "my-project"
    proj.mkdir(parents=True)
    results = list(_scope._reconstruct(_key(proj), str(tmp_path / "Repos")))
    assert results == [proj]


def test_reconstruct_yields_all_existing_interpretations(tmp_path):
    # both ".../Repos/my-project" and ".../Repos/my/project" exist -> both yielded.
    repos = tmp_path / "Repos"
    (repos / "my-project").mkdir(parents=True)
    (repos / "my" / "project").mkdir(parents=True)
    results = list(_scope._reconstruct(_key(repos / "my-project"), str(repos)))
    assert (repos / "my-project") in results
    assert (repos / "my" / "project") in results


def test_reconstruct_prunes_nonexistent_paths(tmp_path):
    # a key whose path doesn't exist yields nothing.
    ghost = tmp_path / "nope" / "missing"
    assert list(_scope._reconstruct(_key(ghost), str(tmp_path))) == []


def test_reconstruct_filters_to_cwd_descendants(tmp_path):
    (tmp_path / "a" / "proj").mkdir(parents=True)
    (tmp_path / "b").mkdir()
    key_a = _key(tmp_path / "a" / "proj")
    # cwd=b: a/proj is not a descendant of b -> excluded
    assert list(_scope._reconstruct(key_a, str(tmp_path / "b"))) == []
    # cwd=a: included
    assert (tmp_path / "a" / "proj") in list(_scope._reconstruct(key_a, str(tmp_path / "a")))


def test_reconstruct_global_yields_any_existing(tmp_path):
    proj = tmp_path / "x" / "y"
    proj.mkdir(parents=True)
    assert proj in list(_scope._reconstruct(_key(proj), None))


def test_reconstruct_excludes_cwd_itself(tmp_path):
    # cwd_str must be a strict ancestor; the cwd dir itself is never yielded.
    proj = tmp_path / "proj"
    proj.mkdir()
    assert list(_scope._reconstruct(_key(proj), str(proj))) == []


# --------------------------------------------------------------------------
# get_scope
# --------------------------------------------------------------------------

def test_get_scope_single(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cwd = tmp_path / "Repos" / "proj"
    cwd.mkdir(parents=True)
    (home / ".claude" / "projects" / _key(cwd)).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    mode, data, c = _scope.get_scope(str(cwd))
    assert mode == "single"
    assert data == _key(cwd)
    assert c == cwd


def test_get_scope_global_when_no_projects_dir(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.setenv("HOME", str(home))
    assert _scope.get_scope(str(cwd)) == ("global", None, None)


def test_get_scope_global_when_no_match(tmp_path, monkeypatch):
    home = tmp_path / "home"
    # projects dir exists but holds an unrelated project
    (home / ".claude" / "projects" / "-somewhere-else").mkdir(parents=True)
    cwd = tmp_path / "Repos"
    cwd.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    assert _scope.get_scope(str(cwd)) == ("global", None, None)


def test_get_scope_parent_rolls_up_descendants(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cwd = tmp_path / "Repos"
    child = cwd / "child"
    child.mkdir(parents=True)
    (home / ".claude" / "projects" / _key(child)).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    mode, data, c = _scope.get_scope(str(cwd))
    assert mode == "parent"
    assert any(reconstructed == child for _, reconstructed in data)
    assert c == cwd


def test_get_scope_single_wins_over_parent(tmp_path, monkeypatch):
    # cwd is itself a project AND has a descendant project -> single takes priority.
    home = tmp_path / "home"
    cwd = tmp_path / "Repos" / "proj"
    child = cwd / "sub"
    child.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    (projects / _key(cwd)).mkdir(parents=True)
    (projects / _key(child)).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    mode, data, _ = _scope.get_scope(str(cwd))
    assert mode == "single"
    assert data == _key(cwd)
