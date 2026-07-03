"""Tests for collect-superpowers-docs — the atlas specs facet collector."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
SCRIPT = SCRIPTS / "collect-superpowers-docs.py"

sys.path.insert(0, str(SCRIPTS))
from _scope import project_key  # noqa: E402


def _world(tmp_path):
    """Fake HOME + two registered projects; alpha has superpowers docs, beta none."""
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    for p in (alpha, beta):
        p.mkdir(parents=True)
        (projects / project_key(p, projects)).mkdir()
    specs = alpha / "docs" / "superpowers" / "specs"
    plans = alpha / "docs" / "superpowers" / "plans"
    specs.mkdir(parents=True)
    plans.mkdir(parents=True)
    (specs / "2026-07-01-x-design.md").write_text(
        "---\nname: x\n---\n\n# X Design\n\nbody\n", encoding="utf-8")
    (specs / "_done-2026-06-30-y-design.md").write_text("# Y Design\n", encoding="utf-8")
    (plans / "untitled-plan.md").write_text("no heading here\n", encoding="utf-8")
    return home


def _run_all(home, cwd):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPT), "--all"],
                          capture_output=True, text=True, env=env, cwd=str(cwd))


def test_emits_rows_with_kind_status_title(tmp_path):
    r = _run_all(_world(tmp_path), tmp_path)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[0] == "PROJECT\tKIND\tSTATUS\tFILE\tTITLE"
    rows = [ln.split("\t") for ln in lines[1:]]
    assert ["alpha", "spec", "live", "2026-07-01-x-design.md", "X Design"] in rows
    assert ["alpha", "spec", "done", "_done-2026-06-30-y-design.md", "Y Design"] in rows
    # no-heading file falls back to the filename stem
    assert ["alpha", "plan", "live", "untitled-plan.md", "untitled-plan"] in rows


def test_project_without_docs_emits_no_rows(tmp_path):
    r = _run_all(_world(tmp_path), tmp_path)
    assert not [ln for ln in r.stdout.splitlines() if ln.startswith("beta\t")]
