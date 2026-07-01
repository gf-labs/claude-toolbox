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
# resolve_key — reverse a project key to its single best existing path
# --------------------------------------------------------------------------

def test_resolve_key_returns_existing_hyphenated_dir(tmp_path):
    # The naive '-'->'/' reverse would yield .../Repos/my/project (missing);
    # resolve_key disambiguates against disk and returns the real hyphenated dir.
    proj = tmp_path / "Repos" / "my-project"
    proj.mkdir(parents=True)
    assert _scope.resolve_key(_key(proj)) == proj


def test_resolve_key_none_when_no_existing_dir(tmp_path):
    ghost = tmp_path / "nope" / "missing"
    assert _scope.resolve_key(_key(ghost)) is None


def test_reconstruct_recovers_underscore_component(tmp_path):
    # The current encoding collapses '_' to '-' just like '/', so the key alone
    # is ambiguous. Reconstruct must recover the real '_claude-plugins' dir by
    # probing disk — the legacy '-'-vs-'/' backtracking alone cannot.
    proj = tmp_path / "business" / "_claude-plugins" / "toolbox"
    proj.mkdir(parents=True)
    key = _scope.project_key(proj)  # lossy: '_' and '/' both -> '-'
    assert proj in list(_scope._reconstruct(key, str(tmp_path)))


def test_resolve_key_recovers_underscore_path(tmp_path):
    # resolve_key over the current (lossy) encoding must invert a path whose
    # component contains '_' — the real claude-toolbox failure mode.
    proj = tmp_path / "business" / "_claude-plugins" / "toolbox"
    proj.mkdir(parents=True)
    key = _scope.project_key(proj)
    assert _scope.resolve_key(key) == proj


# --------------------------------------------------------------------------
# project_key — forward encoding (path -> ~/.claude/projects/ dir name)
# --------------------------------------------------------------------------
# Claude Code encodes a project's cwd into a directory name by replacing every
# non-alphanumeric character with '-'. That rule has changed across versions
# (older builds only replaced '/'), so on one machine the same path can have
# dirs under more than one encoding. project_key probes disk and returns the
# encoding that actually exists, preferring the current rule.

def test_project_key_pure_collapses_all_nonalnum():
    # No projects_dir to probe -> return the current Claude Code encoding:
    # '/', '_', '.', '@', space all collapse to '-'.
    assert _scope.project_key("/Users/x/business/_claude-plugins/ramp") == \
        "-Users-x-business--claude-plugins-ramp"
    assert _scope.project_key("/U/user@example.com/My Drive/.X") == \
        "-U-user-example-com-My-Drive--X"


def test_project_key_resolves_current_encoding_dir(tmp_path):
    # The '_'-collapsing (current) encoding is what exists on disk -> return it.
    projects = tmp_path / "projects"
    real = projects / "-Users-x-business--claude-plugins-ramp"
    real.mkdir(parents=True)
    key = _scope.project_key("/Users/x/business/_claude-plugins/ramp", projects)
    assert key == "-Users-x-business--claude-plugins-ramp"
    assert (projects / key).is_dir()


def test_project_key_falls_back_to_legacy_underscore_dir(tmp_path):
    # Regression guard: a dir created by an older Claude Code (which preserved
    # '_') must still resolve, even though the current rule would collapse it.
    projects = tmp_path / "projects"
    legacy = projects / "-Users-x-business-_claude-plugins-toolbox"
    legacy.mkdir(parents=True)
    key = _scope.project_key("/Users/x/business/_claude-plugins/toolbox", projects)
    assert key == "-Users-x-business-_claude-plugins-toolbox"


def test_project_key_prefers_current_when_both_exist(tmp_path):
    # Same path opened under both encodings -> the current (collapsed) one wins,
    # matching the dir the live session actually uses.
    projects = tmp_path / "projects"
    (projects / "-Users-x-business-_claude-plugins-gfl").mkdir(parents=True)
    (projects / "-Users-x-business--claude-plugins-gfl").mkdir(parents=True)
    key = _scope.project_key("/Users/x/business/_claude-plugins/gfl", projects)
    assert key == "-Users-x-business--claude-plugins-gfl"


def test_project_key_defaults_to_current_when_none_exist(tmp_path):
    # Brand-new project not yet on disk -> current encoding (CC will create it).
    projects = tmp_path / "projects"
    projects.mkdir()
    key = _scope.project_key("/Users/x/business/_claude-plugins/new", projects)
    assert key == "-Users-x-business--claude-plugins-new"


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


def test_get_scope_single_resolves_collapsed_special_char_dir(tmp_path, monkeypatch):
    # cwd contains '_'; only the current-encoding (collapsed) project dir exists.
    # The old naive key (str(cwd).replace('/','-')) preserves '_' and misses it,
    # so it would fall through to 'global'. project_key must resolve it to single.
    home = tmp_path / "home"
    cwd = tmp_path / "Repos" / "_acme" / "svc"
    cwd.mkdir(parents=True)
    collapsed = _scope.project_key(str(cwd))  # current rule: '_' -> '-'
    (home / ".claude" / "projects" / collapsed).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    mode, data, c = _scope.get_scope(str(cwd))
    assert mode == "single"
    assert data == collapsed
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
