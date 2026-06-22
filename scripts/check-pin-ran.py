#!/usr/bin/env python3
"""PreCompact hook: block /compact if /tools:pin hasn't been run this session.

Claude Code pipes the hook payload (including the authoritative ``session_id``)
to this script on stdin, so the current session is read from there rather than
guessed by file mtime — an unrelated JSONL touched more recently (a title edit,
a second session) would otherwise misselect and either false-block a pinned
session or fail open on an unpinned one. Newest-mtime survives only as a
fallback for stdin-less manual invocation.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope, project_key

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
        proj_dir = projects_dir / project_key(git_root, projects_dir)
    except Exception:
        sys.exit(0)  # Can't determine project — allow compact

# Identify the current session. Prefer the session_id from the hook's stdin
# payload (authoritative); fall back to newest-mtime for stdin-less runs.
session_prefix = None
if not sys.stdin.isatty():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        session_prefix = (payload.get("session_id") or "")[:8] or None
    except Exception:
        session_prefix = None

if session_prefix is None:
    jsonl_files = list(proj_dir.glob("*.jsonl"))
    if not jsonl_files:
        sys.exit(0)  # No sessions — allow compact
    session_prefix = max(jsonl_files, key=lambda f: f.stat().st_mtime).stem[:8]

session_log = proj_dir / "memory" / "session-log.md"
if session_log.exists() and f"· {session_prefix}" in session_log.read_text(encoding='utf-8'):
    sys.exit(0)  # Pin was run — allow compact

print(
    f"⚠  Run /tools:pin before /compact (session {session_prefix} not yet logged).",
    file=sys.stderr,
)
sys.exit(2)
