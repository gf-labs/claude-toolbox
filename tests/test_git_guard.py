import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "git_guard", Path(__file__).resolve().parent.parent / "scripts" / "git-guard.py"
)
git_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(git_guard)
classify = git_guard.classify


DENY = [
    ("git reset --hard", "reset-hard"),
    ("git reset --hard HEAD~1", "reset-hard"),
    ("git clean -f", "clean-force"),
    ("git clean -fd", "clean-force"),
    ("git clean -xdf", "clean-force"),
    ("git clean --force", "clean-force"),
    ("git -C /repo clean -fd", "clean-force"),
    ("git branch -D feature/x", "branch-delete-force"),
    ("git branch --delete --force feature/x", "branch-delete-force"),
    ("git checkout .", "checkout-discard"),
    ("git checkout -- src/foo.py", "checkout-discard"),
    ("git checkout -f main", "checkout-discard"),
    ("git restore .", "restore-discard"),
    ("git restore src/foo.py", "restore-discard"),
    ("git add . && git reset --hard", "reset-hard"),
]

ALLOW = [
    "git reset --soft HEAD~1",
    "git reset HEAD file",
    "git push",
    "git push --force",
    "git push origin main",
    "git commit -m x",
    "git checkout develop",
    "git checkout -b feature/new",
    "git status",
    "git clean -n",
    "git branch -d merged",
    "git restore",
    "ls -la",
    "rm -rf build",
    "",
    'git commit -m "unbalanced',   # shlex failure -> fail-open allow
    "echo hi; git status",
]


def test_deny_cases():
    for cmd, rule in DENY:
        v = classify(cmd)
        assert v["action"] == "deny", f"expected deny for {cmd!r}, got {v}"
        assert v["rule"] == rule, f"expected {rule} for {cmd!r}, got {v['rule']}"
        assert v["reason"], f"deny for {cmd!r} must carry a reason"


def test_allow_cases():
    for cmd in ALLOW:
        v = classify(cmd)
        assert v["action"] == "allow", f"expected allow for {cmd!r}, got {v}"


import json
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "git-guard.py"


def _run(payload):
    """Pipe a payload string to the hook; return (returncode, stdout)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def test_smoke_deny_reset_hard():
    rc, out = _run(json.dumps({
        "session_id": "abc", "tool_name": "Bash",
        "tool_input": {"command": "git reset --hard"},
    }))
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "reset --hard" in hso["permissionDecisionReason"]
    assert "!git" in hso["permissionDecisionReason"]


def test_smoke_allow_push():
    rc, out = _run(json.dumps({
        "session_id": "abc", "tool_name": "Bash",
        "tool_input": {"command": "git push --force"},
    }))
    assert rc == 0
    assert out.strip() == ""  # allow == silent


def test_smoke_non_bash_allows():
    rc, out = _run(json.dumps({
        "session_id": "abc", "tool_name": "Edit",
        "tool_input": {"command": "git reset --hard"},
    }))
    assert rc == 0
    assert out.strip() == ""


def test_smoke_malformed_stdin_fails_open():
    rc, out = _run("not json at all {{{")
    assert rc == 0
    assert out.strip() == ""


def test_smoke_compound_uncatchable_fails_open():
    # A reset --hard hidden in command substitution is NOT caught; assert we
    # fail open rather than falsely claim coverage.
    rc, out = _run(json.dumps({
        "session_id": "abc", "tool_name": "Bash",
        "tool_input": {"command": "echo $(git reset --hard)"},
    }))
    assert rc == 0
    assert out.strip() == ""
