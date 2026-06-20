"""Tests for session_naming — the shared session display-name helpers.

These functions were previously copy-pasted across post-save.py and
rename-unnamed.py (and the title read/write loops across four more scripts).
Extracting them into an importable module is what makes them testable at all:
the original copies lived inside scripts that run get_scope() at import time.
"""
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import session_naming  # noqa: E402


# --------------------------------------------------------------------------
# slug
# --------------------------------------------------------------------------

def test_slug_basic_keywords():
    assert session_naming.slug("Fix the login bug") == "fix-login-bug"


def test_slug_drops_skip_words_entirely():
    # every word is a skip word -> empty slug
    assert session_naming.slug("this is my work") == ""


def test_slug_drops_single_characters():
    assert session_naming.slug("a x yy zzz") == "yy-zzz"


def test_slug_caps_at_five_words():
    assert session_naming.slug("alpha beta gamma delta epsilon zeta") == \
        "alpha-beta-gamma-delta-epsilon"


def test_slug_strips_punctuation():
    assert session_naming.slug("foo, bar! baz.") == "foo-bar-baz"


def test_slug_keeps_alphanumeric():
    assert session_naming.slug("v2 release plan") == "v2-release-plan"


def test_slug_empty_input():
    assert session_naming.slug("") == ""


# --------------------------------------------------------------------------
# derive_name
# --------------------------------------------------------------------------

def test_derive_name_strips_branch_conventional_and_version():
    commit = "[main a1b2c3] feat(api): add user auth (v1.2.0)"
    assert session_naming.derive_name(commit, "") == "add-user-auth"


def test_derive_name_master_branch_and_fix_prefix():
    assert session_naming.derive_name("[master deadbee] fix: resolve crash", "") == \
        "resolve-crash"


def test_derive_name_falls_back_to_first_user():
    assert session_naming.derive_name("", "implement the parser") == "implement-parser"


def test_derive_name_strips_slash_command_from_first_user():
    assert session_naming.derive_name("", "/tools:pin checkpoint now") == "checkpoint-now"


def test_derive_name_empty_commit_slug_falls_through_to_user():
    # commit subject is all skip words -> slug empty -> use first_user
    commit = "[main x] chore: and the to"
    assert session_naming.derive_name(commit, "fallback message here") == \
        "fallback-message-here"


def test_derive_name_both_empty():
    assert session_naming.derive_name("", "") == ""


# --------------------------------------------------------------------------
# extract_context
# --------------------------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_extract_context_first_user_string_content(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [
        {"type": "user", "message": {"content": "first question here"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}},
    ])
    commit, first_user = session_naming.extract_context(p)
    assert first_user == "first question here"
    assert commit == ""


def test_extract_context_first_user_list_content(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hello there"}]}},
    ])
    _, first_user = session_naming.extract_context(p)
    assert first_user == "hello there"


def test_extract_context_truncates_first_user_to_150(tmp_path):
    p = tmp_path / "s.jsonl"
    long_msg = "x" * 200
    _write_jsonl(p, [{"type": "user", "message": {"content": long_msg}}])
    _, first_user = session_naming.extract_context(p)
    assert len(first_user) == 150


def test_extract_context_finds_commit_in_tool_result(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [
        {"type": "user", "message": {"content": "do it"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_result", "content": [
                {"type": "text", "text": "[main abc1234] feat: do the thing\n 1 file changed"}
            ]},
        ]}},
    ])
    commit, _ = session_naming.extract_context(p)
    assert commit == "[main abc1234] feat: do the thing"


def test_extract_context_no_user_no_commit(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}])
    commit, first_user = session_naming.extract_context(p)
    assert commit == ""
    assert first_user == ""


# --------------------------------------------------------------------------
# read_title / write_title
# --------------------------------------------------------------------------

def test_read_title_last_wins(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [
        {"type": "custom-title", "customTitle": "first-name", "sessionId": "s"},
        {"type": "custom-title", "customTitle": "second-name", "sessionId": "s"},
    ])
    assert session_naming.read_title(p) == "second-name"


def test_read_title_none_present(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [{"type": "user", "message": {"content": "hi"}}])
    assert session_naming.read_title(p) == ""


def test_read_title_tolerates_corrupt_lines(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text(
        '{ not json\n'
        + json.dumps({"type": "custom-title", "customTitle": "good-name", "sessionId": "s"})
        + "\n",
        encoding="utf-8",
    )
    assert session_naming.read_title(p) == "good-name"


def test_read_title_missing_file_returns_empty(tmp_path):
    assert session_naming.read_title(tmp_path / "does-not-exist.jsonl") == ""


def test_write_title_round_trips(tmp_path):
    p = tmp_path / "abc-123.jsonl"
    p.write_text("", encoding="utf-8")
    session_naming.write_title(p, "my-session-name")
    assert session_naming.read_title(p) == "my-session-name"


def test_write_title_uses_stem_as_session_id(tmp_path):
    p = tmp_path / "abc-123.jsonl"
    p.write_text("", encoding="utf-8")
    session_naming.write_title(p, "n")
    last = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()][-1]
    assert last == {"type": "custom-title", "customTitle": "n", "sessionId": "abc-123"}


def test_write_title_is_append_only(tmp_path):
    p = tmp_path / "abc-123.jsonl"
    p.write_text(json.dumps({"type": "user", "message": {"content": "keep me"}}) + "\n",
                 encoding="utf-8")
    session_naming.write_title(p, "new-name")
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["message"]["content"] == "keep me"
