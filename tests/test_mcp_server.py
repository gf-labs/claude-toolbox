"""Tests for the claude-toolbox MCP server tools and helpers.

server.py imports mcp from its own venv; the system interpreter running these
tests does not have it. server.py falls back to a stub FastMCP when mcp is
absent, which leaves the tool functions as plain importable callables — that
fallback is what makes this file possible.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest

MCP_DIR = Path(__file__).parent.parent / "mcp_server"
sys.path.insert(0, str(MCP_DIR))

import server  # noqa: E402


@pytest.fixture
def projects(monkeypatch, tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    monkeypatch.setattr(server, "PROJECTS_DIR", d)
    return d


@pytest.fixture
def plans(monkeypatch, tmp_path):
    d = tmp_path / "plans"
    d.mkdir()
    monkeypatch.setattr(server, "PLANS_DIR", d)
    return d


def _session(path, *, title=None, first_user=None, last_prompt=None):
    recs = []
    if first_user is not None:
        recs.append({"type": "user", "message": {"content": first_user}})
    if last_prompt is not None:
        recs.append({"type": "last-prompt", "lastPrompt": last_prompt})
    if title is not None:
        recs.append({"type": "custom-title", "customTitle": title, "sessionId": path.stem})
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def test_project_display_takes_last_component():
    assert server._project_display("-Users-foo-Repos-bar") == "bar"


def test_project_display_empty_key():
    assert server._project_display("") == ""


def test_session_metadata_string_content(tmp_path):
    f = tmp_path / "s.jsonl"
    _session(f, title="my-title", first_user="hello world", last_prompt="last thing")
    assert server._session_metadata(f) == {
        "title": "my-title", "first_user": "hello world", "last_prompt": "last thing",
    }


def test_session_metadata_list_content(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text(json.dumps(
        {"type": "user", "message": {"content": [{"type": "text", "text": "list msg"}]}}
    ) + "\n", encoding="utf-8")
    assert server._session_metadata(f)["first_user"] == "list msg"


def test_session_metadata_truncates_to_120(tmp_path):
    f = tmp_path / "s.jsonl"
    _session(f, first_user="x" * 200)
    assert len(server._session_metadata(f)["first_user"]) == 120


def test_session_metadata_missing_file_returns_empties(tmp_path):
    assert server._session_metadata(tmp_path / "nope.jsonl") == {
        "title": "", "first_user": "", "last_prompt": "",
    }


def test_read_session_log_returns_last_n_entries(projects):
    proj = projects / "-x-myproj"
    (proj / "memory").mkdir(parents=True)
    (proj / "memory" / "session-log.md").write_text(
        "## 2026-01-01\n- one\n\n## 2026-01-02\n- two\n\n## 2026-01-03\n- three\n",
        encoding="utf-8",
    )
    out = server._read_session_log("-x-myproj", n_entries=2)
    assert "one" not in out
    assert "two" in out and "three" in out


def test_read_session_log_missing_returns_empty(projects):
    assert server._read_session_log("-x-none") == ""


# --------------------------------------------------------------------------
# search_sessions
# --------------------------------------------------------------------------

def test_search_sessions_matches_and_shapes_result(projects):
    proj = projects / "-x-coolproj"
    proj.mkdir()
    f = proj / "abcdef12-aaaaaaaaaaaaaaaaaaaaaaaaaaaa.jsonl"
    _session(f, title="fix-the-bug", first_user="hello", last_prompt="bye")
    out = json.loads(server.search_sessions("bug"))
    assert len(out) == 1
    assert out[0]["title"] == "fix-the-bug"
    assert out[0]["project"] == "coolproj"
    assert out[0]["session_id"] == f.stem[:8]


def test_search_sessions_searches_first_user_and_last_prompt(projects):
    proj = projects / "-x-p"
    proj.mkdir()
    _session(proj / "s1.jsonl", first_user="parser internals", last_prompt="z")
    _session(proj / "s2.jsonl", last_prompt="deployment pipeline")
    assert len(json.loads(server.search_sessions("parser"))) == 1
    assert len(json.loads(server.search_sessions("deployment"))) == 1


def test_search_sessions_no_match_returns_empty(projects):
    proj = projects / "-x-p"
    proj.mkdir()
    _session(proj / "s.jsonl", title="alpha")
    assert json.loads(server.search_sessions("nonexistent-zzz")) == []


def test_search_sessions_respects_days_window(projects):
    proj = projects / "-x-p"
    proj.mkdir()
    f = proj / "s.jsonl"
    _session(f, title="old-session")
    old = time.time() - 200 * 86400
    os.utime(f, (old, old))
    assert json.loads(server.search_sessions("old", days=90)) == []
    assert len(json.loads(server.search_sessions("old", days=365))) == 1


def test_search_sessions_no_projects_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "PROJECTS_DIR", tmp_path / "nope")
    assert json.loads(server.search_sessions("x")) == []


# --------------------------------------------------------------------------
# list_plans
# --------------------------------------------------------------------------

def test_list_plans_extracts_title_skipping_frontmatter(plans):
    (plans / "my-plan.md").write_text(
        "---\nfoo: bar\n---\n# My Great Plan\n\nbody\n", encoding="utf-8"
    )
    out = json.loads(server.list_plans())
    assert len(out) == 1
    assert out[0]["title"] == "My Great Plan"
    assert out[0]["filename"] == "my-plan.md"
    assert out[0]["line_count"] == 6


def test_list_plans_falls_back_to_stem_when_no_title(plans):
    (plans / "untitled.md").write_text("no heading here\n", encoding="utf-8")
    out = json.loads(server.list_plans())
    assert out[0]["title"] == "untitled"


def test_list_plans_empty_dir(plans):
    assert json.loads(server.list_plans()) == []


def test_list_plans_no_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "PLANS_DIR", tmp_path / "nope")
    assert json.loads(server.list_plans()) == []


# --------------------------------------------------------------------------
# get_session_log
# --------------------------------------------------------------------------

def _make_log(projects, dirname, body="## 2026-01-01\n- did stuff\n"):
    proj = projects / dirname
    (proj / "memory").mkdir(parents=True)
    (proj / "memory" / "session-log.md").write_text(body, encoding="utf-8")
    return proj


def test_get_session_log_lists_available_when_empty_arg(projects):
    _make_log(projects, "-x-myproj")
    out = server.get_session_log("")
    assert "Available projects:" in out
    assert "myproj" in out


def test_get_session_log_returns_log_on_exact_match(projects):
    _make_log(projects, "-x-myproj")
    out = server.get_session_log("myproj")
    assert "myproj — session log" in out
    assert "did stuff" in out


def test_get_session_log_substring_match(projects):
    _make_log(projects, "-x-coolproject")
    out = server.get_session_log("coolpro")
    assert "did stuff" in out


def test_get_session_log_not_found(projects):
    (projects / "-x-myproj").mkdir()
    out = server.get_session_log("zzz-absent")
    assert "not found" in out.lower()


def test_get_session_log_no_projects_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "PROJECTS_DIR", tmp_path / "nope")
    assert server.get_session_log("x") == "No projects directory found."
