#!/usr/bin/env python3
"""Disambiguate same-named session forks (compact continuations).

Claude Code's auto-compact forks a session into a new JSONL that inherits the
prior session's title. The /resume picker then shows two identical rows and
renames them as a *group* (the compact-chain), so you cannot tell them apart or
relabel them from the UI. Per-file titles, however, are read independently — so
writing a distinct title directly to a file disambiguates it in the picker.

This relabels forks at the file level: the newest fork (by last-event timestamp)
keeps the clean name; older forks get a `~MM-DD` stale marker. Idempotent.

Usage:
  relabel-forks.py             # dry-run, current scope
  relabel-forks.py --apply     # write changes, current scope
  relabel-forks.py --all       # dry-run across every project
  relabel-forks.py --path DIR  # target one project-key dir
  combine --all/--path with --apply to write.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_naming import plan_fork_relabels, write_title

args = sys.argv[1:]
apply = '--apply' in args
scan_all = '--all' in args
projects_dir = Path.home() / '.claude' / 'projects'

if '--path' in args:
    idx = args.index('--path')
    if idx + 1 >= len(args):
        print('ERROR: --path requires a value')
        sys.exit(1)
    dirs = [Path(args[idx + 1])]
elif scan_all:
    dirs = sorted(d for d in projects_dir.iterdir() if d.is_dir())
else:
    mode, data, _ = get_scope()
    if mode == 'single':
        dirs = [projects_dir / data]
    elif mode == 'parent':
        dirs = [projects_dir / key for key, _ in data]
    else:
        dirs = sorted(d for d in projects_dir.iterdir() if d.is_dir())

total = 0
written = 0
for d in dirs:
    if not d.exists():
        continue
    actions = plan_fork_relabels(d)
    if not actions:
        continue
    print(f'\n{d.name}')
    for a in actions:
        total += 1
        print(f"  {a['sid']}  {a['current']!r}  →  {a['proposed']!r}   ({a['reason']})")
        if apply:
            if write_title(a['path'], a['proposed']):
                written += 1

if total == 0:
    print('No fork collisions found.')
elif apply:
    print(f'\nRelabeled {written} fork(s).')
else:
    print(f'\nWould relabel {total} fork(s).  Re-run with --apply to write.')
