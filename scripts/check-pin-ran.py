#!/usr/bin/env python3
"""PreCompact hook: block /compact if /tools:pin hasn't been run this session."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

mode, data, cwd = get_scope()

projects_dir = Path.home() / ".claude" / "projects"

if mode == "single":
    proj_dir = projects_dir / data
else:
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        proj_dir = projects_dir / git_root.replace("/", "-")
    except Exception:
        sys.exit(0)  # Can't determine project — allow compact

jsonl_files = list(proj_dir.glob("*.jsonl"))
if not jsonl_files:
    sys.exit(0)  # No sessions — allow compact

current = max(jsonl_files, key=lambda f: f.stat().st_mtime)
session_prefix = current.stem[:8]

session_log = proj_dir / "memory" / "session-log.md"
if session_log.exists() and f"· {session_prefix}" in session_log.read_text():
    sys.exit(0)  # Pin was run — allow compact

print(
    f"⚠  Run /tools:pin before /compact (session {session_prefix} not yet logged).",
    file=sys.stderr,
)
sys.exit(1)
