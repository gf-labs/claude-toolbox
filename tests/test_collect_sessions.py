import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / "collect-sessions.py"), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def test_single_scope_lists_session(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "work" / "alpha"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    repo.mkdir(parents=True)
    key = str(repo).replace("/", "-")
    pd = projects / key
    pd.mkdir()
    f = pd / "sess1234-aaaa.jsonl"
    f.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n", encoding="utf-8")
    now = time.time()
    os.utime(f, (now, now))  # recent -> KEEP

    result = _run(home, repo, "--days", "30")
    assert result.returncode == 0, result.stderr
    line = result.stdout.strip()
    assert line.startswith(f"{key}  sess1234-aaaa  ")
    assert line.endswith("KEEP")
