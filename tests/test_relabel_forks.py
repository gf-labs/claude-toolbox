import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / "relabel-forks.py"), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def _fork_pair(pd, base_title):
    # Two sessions with the same custom-title = a fork collision plan_fork_relabels detects.
    # last-event timestamp must be an ISO string (sliced [:10] for the date marker);
    # the newer one keeps the clean name, the older gets a ~MM-DD suffix.
    pairs = [("aaa11111-aaaa", "2026-07-01T10:00:00Z", 1000),
             ("bbb22222-bbbb", "2026-07-02T10:00:00Z", 2000)]
    for stem, iso, mt in pairs:
        f = pd / f"{stem}.jsonl"
        f.write_text(
            json.dumps({"type": "user", "message": {"content": "x"}, "timestamp": iso}) + "\n" +
            json.dumps({"type": "custom-title", "customTitle": base_title, "sessionId": stem}) + "\n",
            encoding="utf-8")
        os.utime(f, (mt, mt))


def test_all_scans_every_project(tmp_path):
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    for repo in (alpha, beta):
        repo.mkdir(parents=True)
        pd = projects / str(repo).replace("/", "-")
        pd.mkdir()
        _fork_pair(pd, f"{repo.name}-feature")
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run(home, outside, "--all")
    assert result.returncode == 0, result.stderr
    assert str(alpha).replace("/", "-") in result.stdout
    assert str(beta).replace("/", "-") in result.stdout
