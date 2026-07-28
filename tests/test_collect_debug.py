import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(script, home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def _old_session(home, repo, stem):
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    repo.mkdir(parents=True, exist_ok=True)
    pd = projects / str(repo).replace("/", "-")
    pd.mkdir(exist_ok=True)
    f = pd / f"{stem}.jsonl"
    f.write_text(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n", encoding="utf-8")
    old = time.time() - 60 * 86400
    os.utime(f, (old, old))  # 60d old -> matches --days 30 cutoff


def test_collect_debug_flags_old(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "work" / "alpha"
    _old_session(home, repo, "sess1234-aaaa")
    debug = home / ".claude" / "debug"
    debug.mkdir(parents=True)
    (debug / "sess1234-aaaa.log").write_text("x" * 2048, encoding="utf-8")

    result = _run("collect-debug.py", home, repo)
    assert result.returncode == 0, result.stderr
    assert "debug/sess1234-aaaa.log" in result.stdout
    assert result.stdout.strip().endswith("OLD")


def test_collect_file_history_flags_old(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "work" / "alpha"
    _old_session(home, repo, "sess1234-aaaa")
    fh = home / ".claude" / "file-history" / "sess1234-aaaa"
    fh.mkdir(parents=True)
    (fh / "snap.txt").write_text("y" * 2048, encoding="utf-8")

    result = _run("collect-file-history.py", home, repo)
    assert result.returncode == 0, result.stderr
    assert "file-history/sess1234-aaaa" in result.stdout
    assert result.stdout.strip().endswith("OLD")
