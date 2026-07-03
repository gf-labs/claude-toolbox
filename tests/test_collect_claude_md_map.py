import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
SCRIPT = SCRIPTS / "collect-claude-md-map.py"


def _load():
    sys.path.insert(0, str(SCRIPTS))  # so the module's `from _projects import ...` resolves
    spec = importlib.util.spec_from_file_location("collect_claude_md_map", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_memory_status_thresholds(tmp_path):
    mod = _load()
    f = tmp_path / "MEMORY.md"
    f.write_text("\n".join("x" for _ in range(200)))
    assert mod.memory_status(f) == ("200L", "WARN")
    f.write_text("\n".join("x" for _ in range(60)))
    assert mod.memory_status(f) == ("60L", "OK")
    f.write_text("only one line\n")
    assert mod.memory_status(f)[1] == "THIN"
    assert mod.memory_status(tmp_path / "nope.md") == ("none", "MISSING")


def test_claude_md_chain_orders_general_to_specific(tmp_path):
    mod = _load()
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "CLAUDE.md").write_text("global")
    proj = home / "Repos" / "app"
    proj.mkdir(parents=True)
    (home / "Repos" / "CLAUDE.md").write_text("repos")
    (proj / "CLAUDE.md").write_text("proj")
    chain = mod.claude_md_chain(proj, home)
    assert chain == ["~/.claude/CLAUDE.md", "~/Repos/CLAUDE.md", "~/Repos/app/CLAUDE.md"]


def test_claude_md_chain_skips_absent(tmp_path):
    mod = _load()
    home = tmp_path / "home"
    home.mkdir()
    proj = home / "solo"
    proj.mkdir()
    # no CLAUDE.md anywhere -> empty chain
    assert mod.claude_md_chain(proj, home) == []


def test_output_is_tsv_with_header():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    header = result.stdout.splitlines()[0]
    assert header == "CONTAINER\tPROJECT\tCLAUDE_MD_DEPTH\tMEMORY_LINES\tMEMORY_STATUS\tCHAIN"


def test_all_flag_enumerates_globally(tmp_path):
    import os
    home = tmp_path / "home"
    a = tmp_path / "work" / "alpha"
    b = tmp_path / "work" / "beta"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    sys.path.insert(0, str(SCRIPTS))
    from _scope import project_key
    for p in (a, b):
        (projects / project_key(p, projects)).mkdir()
    env = {**os.environ, "HOME": str(home)}
    result = subprocess.run([sys.executable, str(SCRIPT), "--all"],
                            capture_output=True, text=True, env=env, cwd=str(a))
    assert result.returncode == 0, result.stderr
    body = result.stdout
    assert "alpha" in body and "beta" in body
