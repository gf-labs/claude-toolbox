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


# --------------------------------------------------------------------------
# write_title idempotency (the write-amplification fix)
# --------------------------------------------------------------------------

def test_write_title_returns_true_on_write(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("", encoding="utf-8")
    assert session_naming.write_title(p, "name") is True


def test_write_title_noop_when_unchanged(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("", encoding="utf-8")
    session_naming.write_title(p, "same-name")
    # second write with an identical title must NOT append a redundant record
    wrote = session_naming.write_title(p, "same-name")
    assert wrote is False
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


def test_write_title_writes_when_name_changes(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("", encoding="utf-8")
    session_naming.write_title(p, "first")
    assert session_naming.write_title(p, "second") is True
    assert session_naming.read_title(p) == "second"


def test_write_title_force_appends_even_when_unchanged(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("", encoding="utf-8")
    session_naming.write_title(p, "n")
    assert session_naming.write_title(p, "n", force=True) is True
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2


# --------------------------------------------------------------------------
# base_title
# --------------------------------------------------------------------------

def test_base_title_strips_date_suffix():
    assert session_naming.base_title("job-search-main~06-27") == "job-search-main"


def test_base_title_strips_date_and_sid_suffix():
    assert session_naming.base_title("job-search-main~06-27-1a2b") == "job-search-main"


def test_base_title_leaves_clean_name_untouched():
    assert session_naming.base_title("job-search-main") == "job-search-main"


def test_base_title_ignores_non_marker_tilde():
    # `~bad` is not a MM-DD marker, so it must be preserved
    assert session_naming.base_title("weird~name") == "weird~name"


# --------------------------------------------------------------------------
# scan_title_and_ts
# --------------------------------------------------------------------------

def test_scan_title_and_ts_returns_last_of_each(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [
        {"type": "user", "message": {"content": "hi"}, "timestamp": "2026-06-01T00:00:00Z"},
        {"type": "custom-title", "customTitle": "old", "sessionId": "s"},
        {"type": "assistant", "message": {"content": []}, "timestamp": "2026-06-02T10:00:00Z"},
        {"type": "custom-title", "customTitle": "new", "sessionId": "s"},
    ])
    title, ts = session_naming.scan_title_and_ts(p)
    assert title == "new"
    assert ts == "2026-06-02T10:00:00Z"


def test_scan_title_and_ts_no_title(tmp_path):
    p = tmp_path / "s.jsonl"
    _write_jsonl(p, [{"type": "user", "message": {"content": "hi"}, "timestamp": "2026-06-01T00:00:00Z"}])
    title, ts = session_naming.scan_title_and_ts(p)
    assert title == ""
    assert ts == "2026-06-01T00:00:00Z"


# --------------------------------------------------------------------------
# plan_fork_relabels
# --------------------------------------------------------------------------

def _fork_session(proj: Path, stem: str, title: str, last_ts: str) -> None:
    """Write a minimal named session with a last-event timestamp."""
    _write_jsonl(proj / f"{stem}.jsonl", [
        {"type": "user", "message": {"content": "hi"}, "timestamp": "2026-06-01T00:00:00Z"},
        {"type": "assistant", "message": {"content": []}, "timestamp": last_ts},
        {"type": "custom-title", "customTitle": title, "sessionId": stem},
    ])


def test_plan_fork_relabels_demotes_older_collision(tmp_path):
    _fork_session(tmp_path, "live1111-aaaa", "job-search-main", "2026-06-28T12:00:00Z")
    _fork_session(tmp_path, "stale222-bbbb", "job-search-main", "2026-06-27T09:00:00Z")
    actions = session_naming.plan_fork_relabels(tmp_path)
    # live already has the clean name -> only the stale fork is relabeled
    assert len(actions) == 1
    a = actions[0]
    assert a["sid"] == "stale222"
    assert a["current"] == "job-search-main"
    assert a["proposed"] == "job-search-main~06-27"


def test_plan_fork_relabels_promotes_live_to_clean_name(tmp_path):
    # neither fork holds the clean base name -> the newer one is promoted to it
    _fork_session(tmp_path, "live1111-aaaa", "job-search-main~06-28", "2026-06-28T12:00:00Z")
    _fork_session(tmp_path, "stale222-bbbb", "job-search-main~06-27", "2026-06-27T09:00:00Z")
    actions = session_naming.plan_fork_relabels(tmp_path)
    proposals = {a["sid"]: a["proposed"] for a in actions}
    assert proposals["live1111"] == "job-search-main"  # promoted
    assert "stale222" not in proposals  # already correctly marked -> no-op


def test_plan_fork_relabels_no_collision(tmp_path):
    _fork_session(tmp_path, "a1111111-aaaa", "configs-main", "2026-06-28T12:00:00Z")
    _fork_session(tmp_path, "b2222222-bbbb", "configs-scratch", "2026-06-27T09:00:00Z")
    assert session_naming.plan_fork_relabels(tmp_path) == []


def test_plan_fork_relabels_single_session(tmp_path):
    _fork_session(tmp_path, "solo1111-aaaa", "configs-main", "2026-06-28T12:00:00Z")
    assert session_naming.plan_fork_relabels(tmp_path) == []


def test_plan_fork_relabels_idempotent_when_already_marked(tmp_path):
    _fork_session(tmp_path, "live1111-aaaa", "job-search-main", "2026-06-28T12:00:00Z")
    _fork_session(tmp_path, "stale222-bbbb", "job-search-main~06-27", "2026-06-27T09:00:00Z")
    assert session_naming.plan_fork_relabels(tmp_path) == []


def test_plan_fork_relabels_same_date_tiebreaker(tmp_path):
    # two stale forks on the same day -> the second gets a sid tiebreaker suffix
    _fork_session(tmp_path, "live1111-zzzz", "job-search-main", "2026-06-28T12:00:00Z")
    _fork_session(tmp_path, "aaaa1111-bbbb", "job-search-main", "2026-06-27T09:00:00Z")
    _fork_session(tmp_path, "cccc2222-dddd", "job-search-main", "2026-06-27T08:00:00Z")
    proposals = sorted(a["proposed"] for a in session_naming.plan_fork_relabels(tmp_path))
    # newest stale keeps the bare date marker; the next collides and gets its sid appended
    assert proposals == ["job-search-main~06-27", "job-search-main~06-27-cccc"]


def test_plan_fork_relabels_ignores_unnamed_sessions(tmp_path):
    _fork_session(tmp_path, "named111-aaaa", "configs-main", "2026-06-28T12:00:00Z")
    # an unnamed session (no custom-title) must not participate
    _write_jsonl(tmp_path / "unnamed2-bbbb.jsonl", [
        {"type": "user", "message": {"content": "hi"}, "timestamp": "2026-06-28T13:00:00Z"},
    ])
    assert session_naming.plan_fork_relabels(tmp_path) == []
