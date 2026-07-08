"""collect-pin.py emits a CONFIG section reflecting CLAUDE_TOOLBOX_PIN_YES_ALL.

The section must appear even when no project is detected (the script exits early
in that path), so it is emitted before scope resolution. We run in a throwaway
cwd with a fake, empty $HOME so scope resolves to the no-project branch and the
run stays fast.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect-pin.py"


def _run(home: Path, cwd: Path, yes_all_value):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_TOOLBOX_PIN_YES_ALL"}
    env["HOME"] = str(home)
    if yes_all_value is not None:
        env["CLAUDE_TOOLBOX_PIN_YES_ALL"] = yes_all_value
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env, capture_output=True, text=True, cwd=str(cwd),
    )


def _config_yes_all(stdout: str) -> str:
    m = re.search(r"^=== CONFIG ===\nYES_ALL: (yes|no)$", stdout, re.MULTILINE)
    assert m, f"no CONFIG section in output:\n{stdout}"
    return m.group(1)


def test_unset_is_no(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "nowhere"
    cwd.mkdir()
    r = _run(home, cwd, None)
    assert r.returncode == 0, r.stderr
    assert _config_yes_all(r.stdout) == "no"


def test_one_is_yes(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "nowhere"
    cwd.mkdir()
    r = _run(home, cwd, "1")
    assert _config_yes_all(r.stdout) == "yes"


def test_true_mixed_case_is_yes(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "nowhere"
    cwd.mkdir()
    r = _run(home, cwd, "TrUe")
    assert _config_yes_all(r.stdout) == "yes"


def test_zero_is_no(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "nowhere"
    cwd.mkdir()
    r = _run(home, cwd, "0")
    assert _config_yes_all(r.stdout) == "no"
