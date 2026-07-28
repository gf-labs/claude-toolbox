import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(script, home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def _register(home, *repos):
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    for r in repos:
        r.mkdir(parents=True, exist_ok=True)
        (projects / str(r).replace("/", "-")).mkdir(exist_ok=True)
    return projects


def _session(proj, stem, content, mtime):
    f = proj / f"{stem}.jsonl"
    f.write_text(json.dumps({"type": "user", "message": {"content": content}}) + "\n",
                 encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_post_save_global_names_unnamed_across_projects(tmp_path):
    # Two registered projects, cwd is neither -> global scope. Each has an older
    # unnamed session (rename candidate) plus a newer "current" session.
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    projects = _register(home, alpha, beta)
    for repo in (alpha, beta):
        pd = projects / str(repo).replace("/", "-")
        _session(pd, "old-aaaa", f"implement the {repo.name} widget", mtime=1000)
        _session(pd, "new-bbbb", "current work", mtime=2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run("post-save.py", home, outside)
    assert result.returncode == 0, result.stderr
    # Global mode: the most-recent-per-project is named as "current"; both projects
    # touched. Assert a Named line appears and no crash (exact name depends on scope
    # order — pin the stable substring, not the ordering).
    assert "Named:" in result.stdout or "Renamed:" in result.stdout, result.stdout
