"""Regression tests for the rename-unnamed.py --dry-run JSON protocol.

rename-unnamed.py proposes display names for unnamed sessions in scope. In
--dry-run it emits one ``PROPOSAL: {json}`` line per candidate instead of
writing titles. The output is JSON (not a ``|``-delimited string) so titles
containing ``|`` survive — this test pins that contract.

The script resolves its project via scripts/_scope.get_scope(), which returns
('single', <key>, cwd) when ~/.claude/projects/<cwd-key> exists. We build a
fake $HOME whose project key matches the subprocess cwd so resolution is
deterministic and never touches git. The most-recent session per project is
always skipped (it is the live one), so fixtures use an older candidate plus a
newer skip-me file.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rename-unnamed.py"


def _session(proj: Path, stem: str, records: list[dict], mtime: int) -> Path:
    f = proj / f"{stem}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def _run(home: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _proj_dir(home: Path, cwd: Path) -> Path:
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    proj.mkdir(parents=True)
    return proj


def test_dry_run_emits_json_proposal_for_unnamed(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj = _proj_dir(home, cwd)
    # Older = unnamed candidate; newer = most-recent, always skipped.
    _session(proj, "older123-aaaa",
             [{"type": "user", "message": {"content": "implement the cool parser feature"}}],
             mtime=1000)
    _session(proj, "newer456-bbbb",
             [{"type": "user", "message": {"content": "second session"}}],
             mtime=2000)

    result = _run(home, cwd, "--dry-run")
    assert result.returncode == 0, result.stderr

    proposals = [ln for ln in result.stdout.splitlines() if ln.startswith("PROPOSAL: ")]
    assert len(proposals) == 1, result.stdout
    obj = json.loads(proposals[0][len("PROPOSAL: "):])
    assert obj == {
        "path": str(proj / "older123-aaaa.jsonl"),
        "id8": "older123",
        "current_title": "",
        "name": "implement-cool-parser-feature",
    }


def test_dry_run_writes_nothing(tmp_path):
    """--dry-run must not append a custom-title to the candidate file."""
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj = _proj_dir(home, cwd)
    older = _session(proj, "older123-aaaa",
                     [{"type": "user", "message": {"content": "do a thing"}}], mtime=1000)
    _session(proj, "newer456-bbbb",
             [{"type": "user", "message": {"content": "current"}}], mtime=2000)
    before = older.read_text(encoding="utf-8")

    _run(home, cwd, "--dry-run")
    assert older.read_text(encoding="utf-8") == before


def test_titled_session_not_proposed_without_force(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj = _proj_dir(home, cwd)
    # Older already has a custom-title -> gated out unless --force.
    _session(proj, "older123-aaaa", [
        {"type": "user", "message": {"content": "implement the cool parser feature"}},
        {"type": "custom-title", "customTitle": "already-named", "sessionId": "older123-aaaa"},
    ], mtime=1000)
    _session(proj, "newer456-bbbb",
             [{"type": "user", "message": {"content": "current"}}], mtime=2000)

    result = _run(home, cwd, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NONE"


def test_sole_session_is_skipped_as_current(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj = _proj_dir(home, cwd)
    _session(proj, "only123-aaaa",
             [{"type": "user", "message": {"content": "the only session"}}], mtime=1000)

    result = _run(home, cwd, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NONE"
