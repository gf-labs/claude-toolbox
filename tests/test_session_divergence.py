"""Tests for session_divergence — the read-only three-store name divergence check.

A session's display name lives in three stores: the session JSONL ``custom-title``
(the only one claude-toolbox writes), the ``~/.claude/sessions/<pid>.json`` peer
roster (the addresses ``SendMessage``/``ListAgents`` resolve), and
``~/.claude/jobs/<id>/state.json``. A ``/rename`` propagates across a compact-chain
group and updates the stores at slightly different moments, so they drift apart.
This module *reports* the divergence read-only — it never writes the roster or job
stores, which are Claude Code's own live state.
"""
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import session_divergence  # noqa: E402


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# find_divergences — store disagreement (title vs roster vs job name)
# --------------------------------------------------------------------------

def test_find_divergences_flags_store_name_disagreement():
    # one session present in all three stores, carrying three different names
    titles = {"aaaa1111": "js-main"}
    roster = [{"sid": "aaaa1111", "name": "js-main-2"}]
    jobs = [{"sid": "aaaa1111", "name": "job-search-prep",
             "state": "running", "tempo": "active"}]
    result = session_divergence.find_divergences(titles, roster, jobs)
    disagreements = result["store_disagreement"]
    assert len(disagreements) == 1
    assert disagreements[0]["sid"] == "aaaa1111"
    assert disagreements[0]["title"] == "js-main"
    assert disagreements[0]["roster_name"] == "js-main-2"
    assert disagreements[0]["job_name"] == "job-search-prep"


def test_find_divergences_silent_when_all_stores_agree():
    titles = {"aaaa1111": "js-main"}
    roster = [{"sid": "aaaa1111", "name": "js-main"}]
    jobs = [{"sid": "aaaa1111", "name": "js-main",
             "state": "running", "tempo": "active"}]
    result = session_divergence.find_divergences(titles, roster, jobs)
    assert result["store_disagreement"] == []


def test_find_divergences_absence_from_a_store_is_not_disagreement():
    # a title + roster that agree, with no job entry at all — the missing store
    # is not a third, conflicting name
    titles = {"aaaa1111": "js-main"}
    roster = [{"sid": "aaaa1111", "name": "js-main"}]
    result = session_divergence.find_divergences(titles, roster, jobs=[])
    assert result["store_disagreement"] == []


def test_find_divergences_single_store_session_never_flagged():
    # a session known only from its title has nothing to disagree with
    titles = {"aaaa1111": "js-main"}
    result = session_divergence.find_divergences(titles, roster=[], jobs=[])
    assert result["store_disagreement"] == []


# --------------------------------------------------------------------------
# find_divergences — duplicate roster names (ambiguous SendMessage addresses)
# --------------------------------------------------------------------------

def test_find_divergences_flags_duplicate_roster_names():
    # two DISTINCT sessions answering to one roster address — SendMessage to it
    # cannot disambiguate the rows
    roster = [
        {"sid": "aaaa1111", "name": "js-main"},
        {"sid": "bbbb2222", "name": "js-main"},
    ]
    result = session_divergence.find_divergences(titles={}, roster=roster, jobs=[])
    dups = result["duplicate_roster_names"]
    assert len(dups) == 1
    assert dups[0]["name"] == "js-main"
    assert sorted(dups[0]["sids"]) == ["aaaa1111", "bbbb2222"]


def test_find_divergences_unique_roster_names_not_flagged():
    roster = [
        {"sid": "aaaa1111", "name": "alpha"},
        {"sid": "bbbb2222", "name": "beta"},
    ]
    result = session_divergence.find_divergences(titles={}, roster=roster, jobs=[])
    assert result["duplicate_roster_names"] == []


# --------------------------------------------------------------------------
# find_divergences — stale holders (a done job still holding a name)
# --------------------------------------------------------------------------

def test_find_divergences_flags_done_job_still_holding_a_name():
    jobs = [{"sid": "aaaa1111", "name": "js-main", "state": "done",
             "tempo": "idle", "job_id": "job-aaaa"}]
    result = session_divergence.find_divergences(titles={}, roster=[], jobs=jobs)
    stale = result["stale_holders"]
    assert len(stale) == 1
    assert stale[0]["sid"] == "aaaa1111"
    assert stale[0]["name"] == "js-main"
    assert stale[0]["state"] == "done"
    assert stale[0]["job_id"] == "job-aaaa"


def test_find_divergences_running_job_with_name_not_stale():
    jobs = [{"sid": "aaaa1111", "name": "js-main", "state": "running",
             "tempo": "active", "job_id": "job-aaaa"}]
    result = session_divergence.find_divergences(titles={}, roster=[], jobs=jobs)
    assert result["stale_holders"] == []


def test_find_divergences_done_job_without_a_name_not_flagged():
    # a completed job holding no name is not squatting on an address
    jobs = [{"sid": "aaaa1111", "name": None, "state": "done",
             "tempo": "idle", "job_id": "job-aaaa"}]
    result = session_divergence.find_divergences(titles={}, roster=[], jobs=jobs)
    assert result["stale_holders"] == []


def test_find_divergences_stale_holder_with_null_sid():
    # read_jobs tolerates a job with no sessionId; a done job still holding a
    # name squats on an address even when it can't be joined by sid
    jobs = [{"sid": None, "name": "js-main", "state": "done",
             "tempo": "idle", "job_id": "job-x"}]
    stale = session_divergence.find_divergences({}, [], jobs)["stale_holders"]
    assert len(stale) == 1
    assert stale[0]["sid"] is None
    assert stale[0]["name"] == "js-main"


# --------------------------------------------------------------------------
# read_roster — ~/.claude/sessions/<pid>.json (guards lifted from _session.py)
# --------------------------------------------------------------------------

def test_read_roster_parses_entries(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "8315.json").write_text(json.dumps({
        "sessionId": "aaaa1111", "name": "js-main",
        "cwd": "/repo", "startedAt": 123, "nameSince": 456,
    }), encoding="utf-8")
    entries = session_divergence.read_roster(sessions)
    assert len(entries) == 1
    e = entries[0]
    assert e["sid"] == "aaaa1111"
    assert e["name"] == "js-main"
    assert e["pid"] == "8315"


def test_read_roster_tolerates_corrupt_and_nondict(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "bad.json").write_text("{ not json", encoding="utf-8")
    (sessions / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
    (sessions / "ok.json").write_text(
        json.dumps({"sessionId": "s1", "name": "n"}), encoding="utf-8")
    entries = session_divergence.read_roster(sessions)
    assert [e["sid"] for e in entries] == ["s1"]


def test_read_roster_skips_entry_without_session_id(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "x.json").write_text(json.dumps({"name": "orphan"}), encoding="utf-8")
    assert session_divergence.read_roster(sessions) == []


def test_read_roster_missing_dir_returns_empty(tmp_path):
    assert session_divergence.read_roster(tmp_path / "nope") == []


# --------------------------------------------------------------------------
# read_jobs — ~/.claude/jobs/<jobId>/state.json
# --------------------------------------------------------------------------

def test_read_jobs_parses_state(tmp_path):
    jobs = tmp_path / "jobs"
    (jobs / "job-aaaa").mkdir(parents=True)
    (jobs / "job-aaaa" / "state.json").write_text(json.dumps({
        "sessionId": "aaaa1111", "name": "js-main",
        "state": "done", "tempo": "idle",
    }), encoding="utf-8")
    entries = session_divergence.read_jobs(jobs)
    assert len(entries) == 1
    e = entries[0]
    assert e["sid"] == "aaaa1111"
    assert e["name"] == "js-main"
    assert e["state"] == "done"
    assert e["tempo"] == "idle"
    assert e["job_id"] == "job-aaaa"


def test_read_jobs_skips_job_dir_without_state_file(tmp_path):
    jobs = tmp_path / "jobs"
    (jobs / "no-state").mkdir(parents=True)
    (jobs / "ok").mkdir()
    (jobs / "ok" / "state.json").write_text(
        json.dumps({"sessionId": "s1"}), encoding="utf-8")
    assert [e["sid"] for e in session_divergence.read_jobs(jobs)] == ["s1"]


def test_read_jobs_tolerates_corrupt_and_nondict(tmp_path):
    jobs = tmp_path / "jobs"
    (jobs / "bad").mkdir(parents=True)
    (jobs / "bad" / "state.json").write_text("{ not json", encoding="utf-8")
    (jobs / "lst").mkdir()
    (jobs / "lst" / "state.json").write_text("[1, 2]", encoding="utf-8")
    (jobs / "ok").mkdir()
    (jobs / "ok" / "state.json").write_text(
        json.dumps({"sessionId": "s1"}), encoding="utf-8")
    assert [e["sid"] for e in session_divergence.read_jobs(jobs)] == ["s1"]


def test_read_jobs_ignores_stray_non_dir(tmp_path):
    # a real jobs/ dir accumulates macOS cruft (.DS_Store); it must not crash
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    (jobs / ".DS_Store").write_text("junk", encoding="utf-8")
    (jobs / "ok").mkdir()
    (jobs / "ok" / "state.json").write_text(
        json.dumps({"sessionId": "s1"}), encoding="utf-8")
    assert [e["sid"] for e in session_divergence.read_jobs(jobs)] == ["s1"]


def test_read_jobs_missing_dir_returns_empty(tmp_path):
    assert session_divergence.read_jobs(tmp_path / "nope") == []


# --------------------------------------------------------------------------
# collect_titles — session-JSONL custom-title, keyed by session id
# --------------------------------------------------------------------------

def test_collect_titles_maps_titled_sessions_only(tmp_path):
    proj = tmp_path / "projA"
    proj.mkdir()
    _write_jsonl(proj / "aaaa1111.jsonl", [
        {"type": "custom-title", "customTitle": "js-main", "sessionId": "aaaa1111"}])
    _write_jsonl(proj / "bbbb2222.jsonl", [
        {"type": "user", "message": {"content": "hi"}}])  # untitled
    assert session_divergence.collect_titles([proj]) == {"aaaa1111": "js-main"}


def test_collect_titles_spans_multiple_project_dirs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _write_jsonl(a / "s1.jsonl", [
        {"type": "custom-title", "customTitle": "one", "sessionId": "s1"}])
    _write_jsonl(b / "s2.jsonl", [
        {"type": "custom-title", "customTitle": "two", "sessionId": "s2"}])
    assert session_divergence.collect_titles([a, b]) == {"s1": "one", "s2": "two"}


def test_collect_titles_ignores_missing_dir(tmp_path):
    assert session_divergence.collect_titles([tmp_path / "nope"]) == {}


# --------------------------------------------------------------------------
# scan — wire a full (synthetic) ~/.claude layout through the readers + core
# --------------------------------------------------------------------------

def test_scan_end_to_end_synthetic_home(tmp_path):
    # one session whose three stores disagree; its backing job is done
    proj = tmp_path / "projects" / "key"
    proj.mkdir(parents=True)
    _write_jsonl(proj / "aaaa1111.jsonl", [
        {"type": "custom-title", "customTitle": "js-main", "sessionId": "aaaa1111"}])
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "8315.json").write_text(
        json.dumps({"sessionId": "aaaa1111", "name": "js-main-2"}), encoding="utf-8")
    jobs = tmp_path / "jobs"
    (jobs / "job-a").mkdir(parents=True)
    (jobs / "job-a" / "state.json").write_text(json.dumps(
        {"sessionId": "aaaa1111", "name": "js-main", "state": "done", "tempo": "idle"}),
        encoding="utf-8")

    findings = session_divergence.scan(sessions, jobs, [proj])
    assert [f["sid"] for f in findings["store_disagreement"]] == ["aaaa1111"]
    assert [f["sid"] for f in findings["stale_holders"]] == ["aaaa1111"]


# --------------------------------------------------------------------------
# format_report
# --------------------------------------------------------------------------

def test_format_report_states_when_clean():
    empty = {"store_disagreement": [], "duplicate_roster_names": [], "stale_holders": []}
    out = session_divergence.format_report(empty)
    assert "No " in out  # e.g. "No name divergence found."


def test_format_report_lists_every_class(tmp_path):
    findings = {
        "store_disagreement": [
            {"sid": "aaaa1111", "title": "js-main",
             "roster_name": "js-main-2", "job_name": "jp"}],
        "duplicate_roster_names": [
            {"name": "js-main", "sids": ["aaaa1111", "bbbb2222"]}],
        "stale_holders": [
            {"sid": "cccc3333", "name": "old", "state": "done",
             "tempo": "idle", "job_id": "job-c"}],
    }
    out = session_divergence.format_report(findings)
    # store disagreement shows the session and each conflicting name
    assert "aaaa1111" in out and "js-main-2" in out
    # duplicate address shows the shared name and both holders
    assert "bbbb2222" in out
    # stale holder shows the done job and its name
    assert "cccc3333" in out and "done" in out
