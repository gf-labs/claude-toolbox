import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / "collect-session-dirs.py"), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def test_flags_old_session_dir(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "work" / "alpha"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    repo.mkdir(parents=True)
    key = str(repo).replace("/", "-")
    pd = projects / key
    pd.mkdir()
    stem = "sess1234-aaaa"
    f = pd / f"{stem}.jsonl"
    f.write_text(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n", encoding="utf-8")
    old = time.time() - 60 * 86400
    os.utime(f, (old, old))
    sdir = pd / stem  # the session's tool-results dir
    sdir.mkdir()
    (sdir / "blob.txt").write_text("z" * 2048, encoding="utf-8")

    result = _run(home, repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{key}  {stem}/  2K  OLD-DIR"
