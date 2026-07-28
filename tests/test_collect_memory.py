import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(home, cwd):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / "collect-memory.py")],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def test_single_scope_reports_memory_status(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "work" / "alpha"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    repo.mkdir(parents=True)
    key = str(repo).replace("/", "-")
    pd = projects / key
    pd.mkdir()
    (pd / "memory").mkdir()
    (pd / "memory" / "MEMORY.md").write_text("\n".join(f"line {i}" for i in range(60)), encoding="utf-8")

    result = _run(home, repo)
    assert result.returncode == 0, result.stderr
    # 60 lines -> "OK"; printed name is the key.
    assert result.stdout.strip() == f"{key}  60L  OK"
