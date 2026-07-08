import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(home, cwd):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / "collect-session-log.py")],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def _log(pd, date, bullet):
    (pd / "memory").mkdir(parents=True, exist_ok=True)
    (pd / "memory" / "session-log.md").write_text(
        f"# Log\n\n## {date} · abc\n- {bullet}\n", encoding="utf-8")


def test_parent_scope_lists_children(tmp_path):
    # cwd is a container dir with two child projects but is NOT itself registered
    # -> get_scope returns parent.
    home = tmp_path / "home"
    work = tmp_path / "work"
    alpha = work / "alpha"
    beta = work / "beta"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    for repo, date in ((alpha, "2026-07-01"), (beta, "2026-07-02")):
        repo.mkdir(parents=True)
        pd = projects / str(repo).replace("/", "-")
        pd.mkdir()
        _log(pd, date, f"did {repo.name}")

    result = _run(home, work)
    assert result.returncode == 0, result.stderr
    assert "alpha\t2026-07-01\t1" in result.stdout
    assert "beta\t2026-07-02\t1" in result.stdout
