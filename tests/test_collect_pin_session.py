"""collect-pin.py must attribute to the env-var session, not a later-startedAt sibling."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect-pin.py"


def _setup(home: Path, cwd: Path, sessions):
    """sessions: list of (sid, startedAt) → one jsonl + one sessions/*.json each."""
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    (proj / "memory").mkdir(parents=True)
    sdir = home / ".claude" / "sessions"
    sdir.mkdir(parents=True)
    for i, (sid, started) in enumerate(sessions):
        (proj / f"{sid}.jsonl").write_text("{}\n", encoding="utf-8")
        (sdir / f"{i}.json").write_text(
            json.dumps({"cwd": str(cwd), "sessionId": sid, "startedAt": started}),
            encoding="utf-8")
    return proj


def _session_line(home: Path, cwd: Path, env_session):
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    if env_session is not None:
        env["CLAUDE_CODE_SESSION_ID"] = env_session
    r = subprocess.run([sys.executable, str(SCRIPT)], env=env, cwd=str(cwd),
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("SESSION: "):
            return line[len("SESSION: "):].strip()
    raise AssertionError(f"no SESSION line.\nstdout={r.stdout}\nstderr={r.stderr}")


def test_env_var_beats_later_startedat_sibling(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    # decoy002 has the LATER startedAt — the old heuristic would pick it.
    _setup(home, cwd, [("real0001", 100), ("decoy002", 999)])
    assert _session_line(home, cwd, "real0001") == "real0001"


def test_env_unset_preserves_startedat_behavior(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup(home, cwd, [("real0001", 100), ("decoy002", 999)])
    # no env var → highest startedAt wins, exactly as before the change.
    assert _session_line(home, cwd, None) == "decoy002"
