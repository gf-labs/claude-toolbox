"""check-docs.py — docs-consistency gate tests (fixture repos in tmp_path)."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check-docs.py"

README = """# x
## Agents
| Agent | Model | Description |
|-------|-------|-------------|
| `explore` | Haiku | finder |
| `plan` | Sonnet | planner |
## Hooks
| Event | Matcher | Script | What it does |
|-------|---------|--------|--------------|
| `SessionStart` | — | `validate-env.py` | checks env |
| `PreToolUse` | `Bash` | `git-guard.py` | guards |
See [LIBRARY.md](LIBRARY.md).
"""

LIBRARY = "surface\n**2 commands · 1 skills · 2 agents · 3 MCP tools · 2 hook handlers · 2 scripts**\n"

HOOKS = {"hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "python3 x/scripts/validate-env.py"}]}],
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 x/scripts/git-guard.py"}]}],
}}


def make_repo(tmp_path, readme=README, library=LIBRARY, hooks=HOOKS):
    repo = tmp_path / "repo"
    for d in ("agents", "commands", "scripts", "hooks", "skills/sit-rep"):
        (repo / d).mkdir(parents=True)
    for a in ("explore", "plan"):
        (repo / "agents" / (a + ".md")).write_text("x")
    for c in ("pin", "wrap"):
        (repo / "commands" / (c + ".md")).write_text("x")
    for s in ("validate-env.py", "git-guard.py"):
        (repo / "scripts" / s).write_text("x")
    (repo / "skills" / "sit-rep" / "SKILL.md").write_text("x")
    (repo / "hooks" / "hooks.json").write_text(json.dumps(hooks))
    (repo / "README.md").write_text(readme)
    (repo / "LIBRARY.md").write_text(library)
    return repo


def run(repo):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                          capture_output=True, text=True)


def test_consistent_repo_passes(tmp_path):
    result = run(make_repo(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_agent_missing_from_readme_fails(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "agents" / "review.md").write_text("x")
    result = run(repo)
    assert result.returncode == 1 and "review" in result.stdout


def test_hook_script_missing_from_readme_fails(tmp_path):
    hooks = dict(HOOKS["hooks"])
    hooks["PreCompact"] = [{"hooks": [{"type": "command", "command": "python3 x/scripts/check-pin-ran.py"}]}]
    repo = make_repo(tmp_path, hooks={"hooks": hooks})
    (repo / "scripts" / "check-pin-ran.py").write_text("x")
    result = run(repo)   # hooks.json has 3 handlers; README table + LIBRARY line say 2
    assert result.returncode == 1


def test_library_count_drift_fails(tmp_path):
    repo = make_repo(tmp_path, library=LIBRARY.replace("2 scripts", "40 scripts"))
    result = run(repo)
    assert result.returncode == 1 and "scripts" in result.stdout.lower()


def test_broken_relative_link_fails(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "LIBRARY.md").rename(repo / "LIB.md")
    result = run(repo)
    assert result.returncode == 1
