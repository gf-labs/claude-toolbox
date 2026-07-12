"""Unit tests for the current-session resolver (scripts/_session.py).

The resolver prefers the authoritative CLAUDE_CODE_SESSION_ID the harness
exports, falling back to the startedAt heuristic (when a cwd is supplied)
and finally to newest-mtime. env/home are injected so no real session or
$HOME is touched.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _session import current_session_jsonl  # noqa: E402


def _proj(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    p.mkdir()
    return p


def test_env_var_wins_when_jsonl_exists(tmp_path):
    proj = _proj(tmp_path)
    (proj / "real0001.jsonl").write_text("{}\n", encoding="utf-8")
    (proj / "decoy002.jsonl").write_text("{}\n", encoding="utf-8")
    env = {"CLAUDE_CODE_SESSION_ID": "real0001"}
    assert current_session_jsonl(proj, env=env, home=tmp_path) == proj / "real0001.jsonl"


def test_env_var_missing_jsonl_falls_back_to_mtime(tmp_path):
    proj = _proj(tmp_path)
    a = proj / "a0000001.jsonl"
    a.write_text("{}\n", encoding="utf-8")
    b = proj / "b0000002.jsonl"
    b.write_text("{}\n", encoding="utf-8")
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    env = {"CLAUDE_CODE_SESSION_ID": "ghost999"}  # ghost999.jsonl absent here
    assert current_session_jsonl(proj, env=env, home=tmp_path) == b


def test_startedat_winner_when_env_unset(tmp_path):
    proj = _proj(tmp_path)
    (proj / "old00001.jsonl").write_text("{}\n", encoding="utf-8")
    (proj / "new00002.jsonl").write_text("{}\n", encoding="utf-8")
    sessions = tmp_path / ".claude" / "sessions"
    sessions.mkdir(parents=True)
    cwd = tmp_path / "work"
    (sessions / "a.json").write_text(
        json.dumps({"cwd": str(cwd), "sessionId": "old00001", "startedAt": 100}),
        encoding="utf-8")
    (sessions / "b.json").write_text(
        json.dumps({"cwd": str(cwd), "sessionId": "new00002", "startedAt": 200}),
        encoding="utf-8")
    got = current_session_jsonl(proj, project_cwd=cwd, env={}, home=tmp_path)
    assert got == proj / "new00002.jsonl"


def test_mtime_fallback_when_no_sessions_dir(tmp_path):
    proj = _proj(tmp_path)
    a = proj / "a0000001.jsonl"
    a.write_text("{}\n", encoding="utf-8")
    b = proj / "b0000002.jsonl"
    b.write_text("{}\n", encoding="utf-8")
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    assert current_session_jsonl(proj, env={}, home=tmp_path) == b


def test_none_when_no_jsonls(tmp_path):
    proj = _proj(tmp_path)
    assert current_session_jsonl(proj, env={}, home=tmp_path) is None


def test_cross_project_env_id_falls_back(tmp_path):
    # env names a session that lives in ANOTHER project (not in this dir)
    proj = _proj(tmp_path)
    local = proj / "local001.jsonl"
    local.write_text("{}\n", encoding="utf-8")
    env = {"CLAUDE_CODE_SESSION_ID": "foreign9"}  # foreign9.jsonl not in proj
    assert current_session_jsonl(proj, env=env, home=tmp_path) == local


def test_malformed_session_file_is_skipped(tmp_path):
    proj = _proj(tmp_path)
    only = proj / "only0001.jsonl"
    only.write_text("{}\n", encoding="utf-8")
    sessions = tmp_path / ".claude" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "bad.json").write_text("not json at all", encoding="utf-8")
    (sessions / "list.json").write_text("[1, 2, 3]", encoding="utf-8")  # not a dict
    cwd = tmp_path / "work"
    got = current_session_jsonl(proj, project_cwd=cwd, env={}, home=tmp_path)
    assert got == only  # no crash; falls through to mtime
