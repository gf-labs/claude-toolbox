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


def _run(home: Path, cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
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
