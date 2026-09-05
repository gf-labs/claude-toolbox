#!/usr/bin/env python3
"""Report where a session's three name stores disagree (read-only).

A session's display name lives in three stores — the session JSONL custom-title,
the ~/.claude/sessions peer roster (the addresses SendMessage/ListAgents resolve),
and ~/.claude/jobs/<id>/state.json. A /rename propagates across a compact-chain
group and leaves them out of sync. This surfaces the divergence; it never writes
the roster or job stores (Claude Code's own live state). Full evidence chain:
docs/session-rename-propagation.md.

Usage:
  session-name-divergence.py            # scan every project's titles + the global roster/jobs
  session-name-divergence.py --path DIR # narrow the title scan to one project-key dir

The roster and job stores are always read whole — they are not project-scoped,
and a duplicate address can cross projects.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import session_divergence  # noqa: E402
from _projects import enumerate_projects, global_scope  # noqa: E402

args = sys.argv[1:]
home = Path.home()

if '--path' in args:
    idx = args.index('--path')
    if idx + 1 >= len(args):
        print('ERROR: --path requires a value')
        sys.exit(1)
    proj_dirs = [Path(args[idx + 1])]
else:
    proj_dirs = sorted((p.proj_dir for p in enumerate_projects(scope=global_scope())),
                       key=lambda d: d.name)

findings = session_divergence.scan(home / '.claude' / 'sessions',
                                   home / '.claude' / 'jobs',
                                   proj_dirs)
print(session_divergence.format_report(findings))
