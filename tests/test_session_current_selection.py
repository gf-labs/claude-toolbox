"""name-session.py (a mtime-caller) must title the env-var session, not the mtime-newest one."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "name-session.py"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from session_naming import read_title  # noqa: E402


def _setup(home: Path, cwd: Path, *, target_id: str, decoy_id: str):
    key = str(cwd).replace("/", "-")
    proj = home / ".claude" / "projects" / key
    (proj / "memory").mkdir(parents=True)
    tgt = proj / f"{target_id}.jsonl"
    dec = proj / f"{decoy_id}.jsonl"
    tgt.write_text("{}\n", encoding="utf-8")
    dec.write_text("{}\n", encoding="utf-8")
    os.utime(tgt, (1000, 1000))   # target OLDER by mtime
    os.utime(dec, (2000, 2000))   # decoy NEWER by mtime
    return proj, tgt, dec


def _run(home: Path, cwd: Path, env_session):
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    if env_session is not None:
        env["CLAUDE_CODE_SESSION_ID"] = env_session
    return subprocess.run([sys.executable, str(SCRIPT), "my-chosen-name"],
                          env=env, cwd=str(cwd), capture_output=True, text=True)


def test_env_session_gets_titled_not_mtime_newest(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj, tgt, dec = _setup(home, cwd, target_id="realsess", decoy_id="decoysss")
    r = _run(home, cwd, "realsess")
    assert r.returncode == 0, r.stderr
    assert read_title(tgt) == "my-chosen-name"   # env session titled
    assert read_title(dec) == ""                 # mtime-newest decoy untouched


def test_env_unset_titles_mtime_newest(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "work"
    cwd.mkdir()
    proj, tgt, dec = _setup(home, cwd, target_id="realsess", decoy_id="decoysss")
    r = _run(home, cwd, None)
    assert r.returncode == 0, r.stderr
    assert read_title(dec) == "my-chosen-name"   # old behavior: mtime-newest titled
    assert read_title(tgt) == ""
