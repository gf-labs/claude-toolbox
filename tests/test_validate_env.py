"""Tests for validate-env.py's data-policy.json deployment.

validate-env.py (SessionStart hook) copies the canonical data-policy.json into
~/.claude/data/tools/. The deployed copy must refresh when the canonical file
changes — the old ``if not dst.exists()`` guard let it go stale forever (TBX-I-3).

The copy block only runs when CLAUDE_TOOLBOX_ROOT is a real dir, so we point it
at the repo root and redirect HOME to a tmp dir to control the destination. The
source is always the repo's real data-policy.json (resolved from the script
location), so we assert the destination ends up byte-equal to it.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate-env.py"
POLICY_SRC = REPO_ROOT / "data-policy.json"


def _run(home: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home), "CLAUDE_TOOLBOX_ROOT": str(REPO_ROOT)}
    return subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True
    )


def _dst(home: Path) -> Path:
    return home / ".claude" / "data" / "tools" / "data-policy.json"


def test_deploys_policy_when_absent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _run(home)
    assert _dst(home).read_bytes() == POLICY_SRC.read_bytes()


def test_refreshes_stale_deployed_policy(tmp_path):
    """A pre-existing deployed copy that differs from canonical must be refreshed."""
    home = tmp_path / "home"
    dst = _dst(home)
    dst.parent.mkdir(parents=True)
    dst.write_text('{"stale": true}', encoding="utf-8")  # differs from canonical
    _run(home)
    assert _dst(home).read_bytes() == POLICY_SRC.read_bytes()
