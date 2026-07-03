"""Regression tests for collect-status --all: complete and deterministic rollup.

The old grouping picked parents via next() over an unordered set (hash-seed
dependent) and its one-level render silently dropped any project whose picked
ancestor was itself nested. Geometry: a 3-level chain of REGISTERED projects.
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
SCRIPT = SCRIPTS / "collect-status.py"

sys.path.insert(0, str(SCRIPTS))
from _scope import project_key  # noqa: E402


def _fixture_home(tmp_path):
    """Fake HOME with registered projects work > work/alpha > work/alpha/beta."""
    home = tmp_path / "home"
    work = tmp_path / "work"
    alpha = work / "alpha"
    beta = alpha / "beta"
    beta.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    for p in (work, alpha, beta):
        (projects / project_key(p, projects)).mkdir()
    return home


def _run_all(home, cwd, seed=None):
    env = {**os.environ, "HOME": str(home)}
    if seed is not None:
        env["PYTHONHASHSEED"] = str(seed)
    return subprocess.run([sys.executable, str(SCRIPT), "--all"],
                          capture_output=True, text=True, env=env, cwd=str(cwd))


def test_all_is_complete_and_deterministic_across_hash_seeds(tmp_path):
    # Every run must render ALL three projects and produce byte-identical output,
    # regardless of the interpreter's hash seed.
    home = _fixture_home(tmp_path)
    outs = []
    for seed in range(6):
        r = _run_all(home, tmp_path, seed=seed)
        assert r.returncode == 0, r.stderr
        names = {ln.split("\t")[1] for ln in r.stdout.splitlines()[1:] if "\t" in ln}
        assert {"work", "alpha", "beta"} <= names, f"seed {seed} dropped rows: {names}"
        outs.append(r.stdout)
    assert len(set(outs)) == 1, "output varies with hash seed"


def test_container_label_is_nearest_ancestor(tmp_path):
    home = _fixture_home(tmp_path)
    r = _run_all(home, tmp_path)
    assert r.returncode == 0, r.stderr
    rows = {ln.split("\t")[1]: ln.split("\t")[0]
            for ln in r.stdout.splitlines()[1:] if "\t" in ln}
    assert rows["beta"] == "alpha"    # nearest ancestor, not "work" — and not dropped
    assert rows["work"] == "header"   # containers render as headers
    assert rows["alpha"] == "header"  # ...including containers that are themselves nested
