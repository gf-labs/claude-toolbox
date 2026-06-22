"""Regression tests for the PreCompact gate (scripts/check-pin-ran.py).

The gate must BLOCK compaction with exit code 2 when the current session has
not been logged via /tools:pin, and ALLOW it (exit 0) once the session prefix
appears in session-log.md. Exit 2 is the only code Claude Code honors as a
PreCompact block (exit 1 is non-blocking).

The script resolves its project via scripts/_scope.get_scope(), which returns
('single', <key>, cwd) when ~/.claude/projects/<cwd-key> exists. We construct a
fake $HOME whose project key matches the subprocess cwd so resolution is
deterministic and never touches git.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-pin-ran.py"


def _setup_project(home: Path, cwd: Path, *, pinned: bool) -> None:
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    (proj / "memory").mkdir(parents=True)
    (proj / "abcd1234.jsonl").write_text("{}\n", encoding="utf-8")
    log = proj / "memory" / "session-log.md"
    if pinned:
        log.write_text(
            "# log\n\n## 2026-06-19 · abcd1234\n- pinned\n", encoding="utf-8"
        )
    else:
        log.write_text("# log\n", encoding="utf-8")


def _run(
    home: Path, cwd: Path, *, session_id: str | None = None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    # Claude Code pipes the PreCompact payload (incl. session_id) on stdin.
    # session_id=None simulates a stdin-less manual run (empty input).
    stdin_data = (
        json.dumps({"session_id": session_id, "hook_event_name": "PreCompact"})
        if session_id is not None
        else ""
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def test_blocks_with_exit_2_when_not_pinned(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup_project(home, cwd, pinned=False)
    result = _run(home, cwd)
    assert result.returncode == 2
    assert "Run /tools:pin" in result.stderr


def test_allows_with_exit_0_when_pinned(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup_project(home, cwd, pinned=True)
    result = _run(home, cwd)
    assert result.returncode == 0


def _setup_two_sessions(
    home: Path,
    cwd: Path,
    *,
    current_id: str,
    current_pinned: bool,
    other_id: str,
    other_pinned: bool,
    other_newer: bool,
) -> None:
    """Two sessions in one project, the 'other' optionally newer by mtime.

    Lets us prove the gate keys off the authoritative session_id (from stdin),
    not whichever JSONL was touched most recently.
    """
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    (proj / "memory").mkdir(parents=True)
    cur = proj / f"{current_id}.jsonl"
    oth = proj / f"{other_id}.jsonl"
    cur.write_text("{}\n", encoding="utf-8")
    oth.write_text("{}\n", encoding="utf-8")
    older, newer = (cur, oth) if other_newer else (oth, cur)
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    lines = ["# log\n"]
    if current_pinned:
        lines.append(f"\n## 2026-06-19 · {current_id[:8]}\n- pinned\n")
    if other_pinned:
        lines.append(f"\n## 2026-06-18 · {other_id[:8]}\n- pinned\n")
    (proj / "memory" / "session-log.md").write_text("".join(lines), encoding="utf-8")


def test_allows_pinned_current_even_when_newer_unrelated_session_unlogged(tmp_path):
    # TBX-N2 (false-block direction): the CURRENT session IS pinned, but an
    # unrelated session has a newer mtime and is NOT logged. max(mtime) would
    # misread the unlogged session and block. The gate must allow (exit 0).
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup_two_sessions(
        home,
        cwd,
        current_id="aaaaaaaa",
        current_pinned=True,
        other_id="bbbbbbbb",
        other_pinned=False,
        other_newer=True,
    )
    result = _run(home, cwd, session_id="aaaaaaaa-1111-2222-3333-444444444444")
    assert result.returncode == 0, result.stderr


def test_blocks_unpinned_current_even_when_newer_session_is_logged(tmp_path):
    # TBX-N2 (fail-open direction): the CURRENT session is NOT pinned, but an
    # older logged session has the newest mtime. max(mtime) would read the
    # logged session and wrongly allow. The gate must block (exit 2).
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup_two_sessions(
        home,
        cwd,
        current_id="aaaaaaaa",
        current_pinned=False,
        other_id="bbbbbbbb",
        other_pinned=True,
        other_newer=True,
    )
    result = _run(home, cwd, session_id="aaaaaaaa-1111-2222-3333-444444444444")
    assert result.returncode == 2, "gate must block when the CURRENT session is unlogged"
