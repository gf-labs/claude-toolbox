"""post-save.py must treat the env-var session as current (Named), not an 'other' (Renamed).

Fixture: the env session carries extractable context; the decoy is empty and
mtime-newer. With the env var, the env session is NAMED and the decoy skipped;
without it, current=decoy (mtime, no context, unnamed→no name) and the env
session becomes an 'other' with context → RENAMED. The Named-vs-Renamed split
is exactly the behavior this task changes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "post-save.py"


def _user_line(text: str) -> str:
    return json.dumps({"type": "user", "message": {"content": text}})


def _setup(home: Path, cwd: Path, *, current_id: str, decoy_id: str):
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    (proj / "memory").mkdir(parents=True)
    cur = proj / f"{current_id}.jsonl"
    dec = proj / f"{decoy_id}.jsonl"
    cur.write_text(_user_line("add the resolver helper") + "\n", encoding="utf-8")
    dec.write_text("{}\n", encoding="utf-8")
    os.utime(cur, (1000, 1000))   # current is OLDER by mtime
    os.utime(dec, (2000, 2000))   # decoy is NEWER by mtime
    return proj


def _run(home: Path, cwd: Path, env_session):
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    if env_session is not None:
        env["CLAUDE_CODE_SESSION_ID"] = env_session
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, cwd=str(cwd),
                          capture_output=True, text=True)


def test_env_session_named_as_current(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup(home, cwd, current_id="realsess", decoy_id="decoysss")
    r = _run(home, cwd, "realsess")
    assert "Named:" in r.stdout, r.stdout
    assert "Renamed:" not in r.stdout, r.stdout


def test_env_unset_names_via_mtime_last(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    _setup(home, cwd, current_id="realsess", decoy_id="decoysss")
    r = _run(home, cwd, None)
    # current=decoy (mtime-newest, empty → no name); realsess is an 'other' → Renamed
    assert "Renamed:" in r.stdout, r.stdout
