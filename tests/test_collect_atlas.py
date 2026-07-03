import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
SCRIPT = SCRIPTS / "collect-atlas.py"


def _load():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("collect_atlas", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_defaults_to_all_project_facets():
    r = _load().parse_args([])
    assert r["facets"] == ["projects", "sessions", "memory", "plans", "claude.md"]
    assert "plugins" not in r["facets"]  # the one global facet stays opt-in
    assert r["project"] is None and r["depth"] == "compact"
    assert r["stale"] is False and r["errors"] == []


def test_parse_multiple_facets_dedup_and_order():
    r = _load().parse_args(["plans", "projects", "plans"])
    assert r["facets"] == ["plans", "projects"]


def test_parse_project_and_full():
    r = _load().parse_args(["memory", "--project", "ramp", "--full"])
    assert r["facets"] == ["memory"] and r["project"] == "ramp" and r["depth"] == "full"


def test_parse_stale_only_has_no_default_facet():
    r = _load().parse_args(["--stale"])
    assert r["stale"] is True and r["facets"] == []


def test_parse_unknown_facet_records_error():
    r = _load().parse_args(["bogus"])
    assert any("unknown facet" in e for e in r["errors"])


def test_parse_project_without_name_records_error():
    r = _load().parse_args(["--project"])
    assert any("--project requires" in e for e in r["errors"])


def test_dry_run_echoes_request_only():
    result = subprocess.run([sys.executable, str(SCRIPT), "--dry-run", "plans", "--full"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "=== REQUEST ===" in result.stdout
    assert "FACETS: plans" in result.stdout
    assert "DEPTH: full" in result.stdout
    # dry-run must NOT shell out to collectors
    assert "=== PLANS ===" not in result.stdout


def test_default_dispatch_emits_projects_section():
    # smoke: real run against the live ~/.claude/projects
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "=== REQUEST ===" in result.stdout
    assert "=== PROJECTS ===" in result.stdout


def test_resolve_project_unknown_name_reports_reason():
    mod = _load()
    key, reason = mod.resolve_project("definitely-not-a-real-project-xyz")
    assert key is None
    assert "no project named" in reason


def test_render_request_contains_all_fields():
    mod = _load()
    s = mod.render_request(mod.parse_args(["memory", "--project", "ramp", "--stale"]))
    assert "FACETS: memory" in s
    assert "PROJECT: ramp" in s
    assert "STALE: yes" in s


def test_resolve_project_finds_projects_outside_ambient_scope(tmp_path, monkeypatch):
    # --project <name> must resolve OTHER projects even when cwd is inside one (single scope).
    home = tmp_path / "home"
    a = tmp_path / "work" / "alpha"
    b = tmp_path / "work" / "beta"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    sys.path.insert(0, str(SCRIPTS))
    from _scope import project_key
    monkeypatch.setenv("HOME", str(home))
    for p in (a, b):
        (projects / project_key(p, projects)).mkdir()
    monkeypatch.chdir(a)
    key, display = _load().resolve_project("beta")
    assert key is not None
    assert display == "beta"


def test_parse_all_flag():
    mod = _load()
    assert mod.parse_args(["--all"])["all"] is True
    assert mod.parse_args([])["all"] is False


def _two_project_home(tmp_path, monkeypatch):
    """Fake HOME with sibling registered projects alpha and beta; cwd -> alpha."""
    home = tmp_path / "home"
    a = tmp_path / "work" / "alpha"
    b = tmp_path / "work" / "beta"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    sys.path.insert(0, str(SCRIPTS))
    from _scope import project_key
    monkeypatch.setenv("HOME", str(home))
    for p in (a, b):
        (projects / project_key(p, projects)).mkdir()
    monkeypatch.chdir(a)


def test_default_scope_is_subtree_from_inside_a_project(tmp_path, monkeypatch):
    # Default lens = current project (+ nested children); sibling projects stay out.
    _two_project_home(tmp_path, monkeypatch)
    mod = _load()
    out = mod.emit(mod.parse_args(["claude.md"]))
    assert "=== CLAUDE.MD ===" in out
    assert "SCOPE: subtree" in out
    assert "alpha" in out
    assert "beta" not in out


def test_all_flag_widens_to_every_project(tmp_path, monkeypatch):
    # --all restores the whole-machine map from the same cwd.
    _two_project_home(tmp_path, monkeypatch)
    mod = _load()
    out = mod.emit(mod.parse_args(["claude.md", "--all"]))
    assert "SCOPE: all" in out
    assert "alpha" in out and "beta" in out


def test_parse_dir_flag():
    mod = _load()
    assert mod.parse_args(["--dir", "work"])["dir"] == "work"
    assert mod.parse_args([])["dir"] is None
    assert mod.parse_args(["--dir"])["errors"]


def test_dir_flag_anchors_at_named_dir(tmp_path, monkeypatch):
    # --dir takes a bare component name or a filesystem path; either way the lens
    # is exactly the anchor's subtree — cwd plays no part, and the anchor dir
    # itself need not be a registered project.
    home = tmp_path / "home"
    work = tmp_path / "work"  # NOT registered — still a valid anchor
    alpha = work / "alpha"
    gamma = tmp_path / "elsewhere" / "gamma"
    alpha.mkdir(parents=True)
    gamma.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    sys.path.insert(0, str(SCRIPTS))
    from _scope import project_key
    monkeypatch.setenv("HOME", str(home))
    for p in (alpha, gamma):
        (projects / project_key(p, projects)).mkdir()
    monkeypatch.chdir(gamma)
    mod = _load()
    for value in ("work", str(work)):  # name-match form and path form
        out = mod.emit(mod.parse_args(["claude.md", "--dir", value]))
        assert "SCOPE: dir" in out
        assert "alpha" in out
        assert "gamma" not in out


def test_dir_flag_errors_when_unresolvable(tmp_path, monkeypatch):
    _two_project_home(tmp_path, monkeypatch)
    mod = _load()
    out = mod.emit(mod.parse_args(["claude.md", "--dir", "nonesuch"]))
    assert "=== ERROR ===" in out
    assert "nonesuch" in out


def test_sessions_facet_narrows_to_subtree(tmp_path, monkeypatch):
    # sessions is a normal narrowable facet: subtree default keeps only the
    # current project's rows; --all restores every project's sessions.
    _two_project_home(tmp_path, monkeypatch)  # cwd -> alpha
    projects = tmp_path / "home" / ".claude" / "projects"
    from _scope import project_key
    for name in ("alpha", "beta"):
        p = tmp_path / "work" / name
        d = projects / project_key(p, projects)
        (d / f"{name}0000-0000.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": "x"},
                        "timestamp": "2026-06-02T10:00:00Z"}) + "\n" +
            json.dumps({"type": "custom-title", "customTitle": f"{name}-sess",
                        "sessionId": f"{name}0000-0000"}) + "\n",
            encoding="utf-8")
    mod = _load()
    out = mod.emit(mod.parse_args(["sessions"]))
    assert "=== SESSIONS ===" in out
    assert "alpha-sess" in out
    assert "beta-sess" not in out
    out_all = mod.emit(mod.parse_args(["sessions", "--all"]))
    assert "alpha-sess" in out_all and "beta-sess" in out_all
