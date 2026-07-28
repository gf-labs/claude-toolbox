"""Tests for collect-session-list.py — the atlas sessions facet collector.

(Distinct from collect-sessions.py, the cleanup age/size inventory.)
Fixture sessions follow the real JSONL shape: timestamped event lines plus a
trailing custom-title record; the filename stem is the session id.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
SCRIPT = SCRIPTS / "collect-session-list.py"

sys.path.insert(0, str(SCRIPTS))
from _scope import project_key  # noqa: E402


def _session(proj_dir, stem, title, last_ts):
    records = [
        {"type": "user", "message": {"content": "hi"}, "timestamp": "2026-06-01T00:00:00Z"},
        {"type": "assistant", "message": {"content": []}, "timestamp": last_ts},
    ]
    if title:
        records.append({"type": "custom-title", "customTitle": title, "sessionId": stem})
    (proj_dir / f"{stem}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _home_with_sessions(tmp_path):
    """alpha: one titled + one newer unnamed session; beta: one titled session."""
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    dirs = {}
    for p in (alpha, beta):
        p.mkdir(parents=True)
        d = projects / project_key(p, projects)
        d.mkdir()
        dirs[p.name] = d
    _session(dirs["alpha"], "aaa11111-1111", "alpha-work", "2026-06-02T10:00:00Z")
    _session(dirs["alpha"], "aaa22222-2222", "", "2026-06-03T10:00:00Z")
    _session(dirs["beta"], "bbb11111-1111", "beta-work", "2026-06-04T10:00:00Z")
    return home, alpha


def _run(home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=env, cwd=str(cwd))


def test_all_lists_titles_dates_and_placeholders(tmp_path):
    home, _alpha = _home_with_sessions(tmp_path)
    r = _run(home, tmp_path, "--all")
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[0] == "PROJECT\tSESSION\tTITLE\tLAST_EVENT"
    by_stem = {row[1]: row for row in (ln.split("\t") for ln in lines[1:] if ln)}
    assert by_stem["aaa11111-1111"] == ["alpha", "aaa11111-1111", "alpha-work", "2026-06-02"]
    assert by_stem["aaa22222-2222"][2] == "—"  # unnamed session -> em-dash
    assert by_stem["bbb11111-1111"][0] == "beta"


def test_newest_last_event_first_within_project(tmp_path):
    home, _alpha = _home_with_sessions(tmp_path)
    r = _run(home, tmp_path, "--all")
    stems = [ln.split("\t")[1] for ln in r.stdout.splitlines()[1:] if ln.startswith("alpha\t")]
    assert stems == ["aaa22222-2222", "aaa11111-1111"]  # by event ts, newest first


def test_ambient_scope_lists_only_current_project(tmp_path):
    home, alpha = _home_with_sessions(tmp_path)
    r = _run(home, alpha)  # no --all, cwd inside project alpha
    assert r.returncode == 0, r.stderr
    body = [ln for ln in r.stdout.splitlines()[1:] if ln]
    assert body and all(ln.startswith("alpha\t") for ln in body)


def test_tolerates_corrupt_lines(tmp_path):
    home, alpha = _home_with_sessions(tmp_path)
    projects = home / ".claude" / "projects"
    d = projects / project_key(alpha, projects)
    (d / "ccc33333-3333.jsonl").write_text(
        'not json\n{"type": "user", "timestamp": "2026-06-05T00:00:00Z"}\n', encoding="utf-8")
    r = _run(home, tmp_path, "--all")
    assert r.returncode == 0, r.stderr
    assert "ccc33333-3333" in r.stdout
