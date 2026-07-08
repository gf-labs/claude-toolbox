"""save-pin-config.py persists CLAUDE_TOOLBOX_PIN_YES_ALL into settings.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "save-pin-config.py"


def _run(home: Path):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env, capture_output=True, text=True,
    )


def _settings(home: Path) -> Path:
    p = home / ".claude" / "settings.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def test_sets_key_preserving_others(tmp_path):
    home = tmp_path / "home"
    s = _settings(home)
    s.write_text(json.dumps({
        "env": {"CLAUDE_TOOLBOX_ROOT": "/x"},
        "permissions": {"allow": ["Bash"]},
    }), encoding="utf-8")

    r = _run(home)
    assert r.returncode == 0, r.stderr
    data = json.loads(s.read_text(encoding="utf-8"))
    assert data["env"]["CLAUDE_TOOLBOX_PIN_YES_ALL"] == "1"
    assert data["env"]["CLAUDE_TOOLBOX_ROOT"] == "/x"       # preserved
    assert data["permissions"] == {"allow": ["Bash"]}       # preserved


def test_creates_missing_settings(tmp_path):
    home = tmp_path / "home"
    r = _run(home)
    assert r.returncode == 0, r.stderr
    data = json.loads((_settings(home)).read_text(encoding="utf-8"))
    assert data["env"]["CLAUDE_TOOLBOX_PIN_YES_ALL"] == "1"


def test_idempotent(tmp_path):
    home = tmp_path / "home"
    _run(home)
    r2 = _run(home)
    assert r2.returncode == 0
    data = json.loads((_settings(home)).read_text(encoding="utf-8"))
    assert data["env"]["CLAUDE_TOOLBOX_PIN_YES_ALL"] == "1"


def test_malformed_json_is_not_clobbered(tmp_path):
    home = tmp_path / "home"
    s = _settings(home)
    s.write_text("{ not valid json", encoding="utf-8")
    r = _run(home)
    assert r.returncode == 1
    assert s.read_text(encoding="utf-8") == "{ not valid json"  # untouched


def test_env_not_object_errors(tmp_path):
    home = tmp_path / "home"
    s = _settings(home)
    s.write_text(json.dumps({"env": "oops"}), encoding="utf-8")
    r = _run(home)
    assert r.returncode == 1
