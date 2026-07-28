"""Tests for _projects — typed enumeration over _scope and the scope-idiom helpers."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _projects  # noqa: E402
from _projects import Project  # noqa: E402
from _scope import project_key  # noqa: E402


def test_enumerate_single(tmp_path):
    p = tmp_path / "repo"
    p.mkdir()
    projs = _projects.enumerate_projects(scope=("single", "-k", p), projects_dir=tmp_path / "pd")
    assert len(projs) == 1
    pr = projs[0]
    assert (pr.key, pr.path, pr.name, pr.container) == ("-k", p, "repo", None)
    assert pr.proj_dir == tmp_path / "pd" / "-k"


def test_enumerate_parent_lists_children(tmp_path):
    a = tmp_path / "root" / "a"
    b = tmp_path / "root" / "b"
    scope = ("parent", [("-a", a), ("-b", b)], tmp_path / "root")
    projs = _projects.enumerate_projects(scope=scope, projects_dir=tmp_path / "pd")
    assert {p.name for p in projs} == {"a", "b"}
    assert all(p.container is None for p in projs)  # siblings, neither nests


def test_enumerate_global_same_shape_as_parent(tmp_path):
    a = tmp_path / "x" / "a"
    b = tmp_path / "y" / "b"
    scope = ("global", [("-a", a), ("-b", b)], tmp_path)
    projs = _projects.enumerate_projects(scope=scope, projects_dir=tmp_path / "pd")
    assert {p.name for p in projs} == {"a", "b"}


def test_enumerate_assigns_container_on_real_nesting(tmp_path):
    parent = tmp_path / "mono"
    child = tmp_path / "mono" / "pkg"
    scope = ("global", [("-mono", parent), ("-pkg", child)], tmp_path)
    by_name = {p.name: p for p in _projects.enumerate_projects(scope=scope, projects_dir=tmp_path / "pd")}
    assert by_name["pkg"].container == "mono"
    assert by_name["mono"].container is None


def test_enumerate_nonproject_intermediate_is_not_a_parent(tmp_path):
    # sibling projects share an intermediate dir that is NOT itself a project ->
    # neither nests (a grouping dir that is not itself a project).
    a = tmp_path / "_grp" / "a"
    b = tmp_path / "_grp" / "b"
    scope = ("global", [("-a", a), ("-b", b)], tmp_path)
    projs = _projects.enumerate_projects(scope=scope, projects_dir=tmp_path / "pd")
    assert all(p.container is None for p in projs)


def test_enumerate_container_is_nearest_ancestor(tmp_path):
    # 3-level chain: each project's container is its NEAREST enumerated ancestor,
    # deterministically (longest path prefix), not an arbitrary matching one.
    a = tmp_path / "a"
    b = tmp_path / "a" / "b"
    c = tmp_path / "a" / "b" / "c"
    scope = ("global", [("-a", a), ("-b", b), ("-c", c)], tmp_path)
    by_name = {p.name: p for p in _projects.enumerate_projects(scope=scope, projects_dir=tmp_path / "pd")}
    assert by_name["c"].container == "b"
    assert by_name["b"].container == "a"
    assert by_name["a"].container is None


# --- scoped_keys ---
def test_scoped_keys_single():
    assert _projects.scoped_keys(scope=("single", "-k", Path("/x"))) == {"-k"}


def test_scoped_keys_parent():
    scope = ("parent", [("-a", Path("/a")), ("-b", Path("/b"))], Path("/"))
    assert _projects.scoped_keys(scope=scope) == {"-a", "-b"}


def test_scoped_keys_global_is_none():
    assert _projects.scoped_keys(scope=("global", [("-a", Path("/a"))], Path("/"))) is None


# --- group ---
def test_group_nests_by_container():
    root = Project("-r", Path("/mono"), "mono", None, Path("/pd/-r"))
    child = Project("-c", Path("/mono/pkg"), "pkg", "mono", Path("/pd/-c"))
    g = _projects.group([root, child])
    assert g[None] == [root]
    assert g["mono"] == [child]


# --- stale_keys ---
def test_stale_keys_flags_orphan_no_dir(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "-nonexistent-path-xyz").mkdir()
    orphaned, unscoped = _projects.stale_keys(projects_dir=projects, active_keys=set())
    assert ("-nonexistent-path-xyz", "no dir on disk") in orphaned


def test_stale_keys_flags_duplicate_no_leading_dash(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "-Users-x-repo").mkdir()
    (projects / "Users-x-repo").mkdir()  # duplicate encoding, no leading dash
    orphaned, _ = _projects.stale_keys(projects_dir=projects, active_keys={"-Users-x-repo"})
    assert ("Users-x-repo", "duplicate (no leading dash)") in orphaned


def test_stale_keys_skips_active(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "-ghost").mkdir()
    orphaned, unscoped = _projects.stale_keys(projects_dir=projects, active_keys={"-ghost"})
    assert orphaned == [] and unscoped == []


# --- global_scope ---
def test_global_scope_ignores_ambient_single_scope(tmp_path, monkeypatch):
    # From inside a registered project (ambient scope = single), global_scope()
    # must still see every project on the machine — the atlas regression case.
    home = tmp_path / "home"
    a = tmp_path / "work" / "alpha"
    b = tmp_path / "work" / "beta"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    for p in (a, b):
        (projects / project_key(p, projects)).mkdir()
    monkeypatch.chdir(a)
    mode, data, _cwd = _projects.global_scope()
    assert mode == "global"
    assert {path for _, path in data} == {a, b}


# --- subtree_projects ---
def _register(home, *paths):
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
        (projects / project_key(p, projects)).mkdir(exist_ok=True)


def test_subtree_from_leaf_is_just_the_leaf(tmp_path, monkeypatch):
    # From (a subdir of) a leaf project, the subtree is the project itself — siblings stay out.
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    _register(home, alpha, beta)
    src = alpha / "src"
    src.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(src)
    assert {p.name for p in _projects.subtree_projects()} == {"alpha"}


def test_subtree_from_container_includes_nested(tmp_path, monkeypatch):
    home = tmp_path / "home"
    work = tmp_path / "work"
    alpha = work / "alpha"
    gamma = tmp_path / "elsewhere" / "gamma"
    _register(home, work, alpha, gamma)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(work)
    assert {p.name for p in _projects.subtree_projects()} == {"work", "alpha"}


def test_subtree_anchors_to_innermost_containing_project(tmp_path, monkeypatch):
    # cwd inside nested project alpha (itself inside registered work): anchor to alpha, not work.
    home = tmp_path / "home"
    work = tmp_path / "work"
    alpha = work / "alpha"
    _register(home, work, alpha)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(alpha)
    assert {p.name for p in _projects.subtree_projects()} == {"alpha"}


def test_subtree_outside_any_project_falls_back_to_all(tmp_path, monkeypatch):
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    _register(home, alpha, beta)
    outside = tmp_path / "nowhere"
    outside.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(outside)
    assert {p.name for p in _projects.subtree_projects()} == {"alpha", "beta"}


def test_projects_under_anchors_at_the_dir_itself(tmp_path, monkeypatch):
    # An UNREGISTERED dir is a valid anchor: exactly the projects under it —
    # no snapping out to an enclosing registered project. (--dir semantics)
    home = tmp_path / "home"
    work = tmp_path / "work"  # deliberately NOT registered
    alpha = work / "alpha"
    beta = work / "beta"
    gamma = tmp_path / "elsewhere" / "gamma"
    _register(home, alpha, beta, gamma)
    monkeypatch.setenv("HOME", str(home))
    assert {p.name for p in _projects.projects_under(work)} == {"alpha", "beta"}
