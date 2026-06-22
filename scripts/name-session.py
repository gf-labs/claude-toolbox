#!/usr/bin/env python3
"""Write a custom-title record to a session JSONL.

Usage:
  python3 name-session.py "short-name-here" [--force]
  python3 name-session.py "short-name-here" --path /path/to/session.jsonl [--force]

Without --path: targets the current (most recent) session in scope.
With --path: targets the specified JSONL file directly.
Skips silently if session already has a custom-title (unless --force).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope, project_key
from session_naming import read_title, write_title

args = sys.argv[1:]
force = '--force' in args

# Extract --path value
explicit_path = None
if '--path' in args:
    idx = args.index('--path')
    if idx + 1 < len(args):
        explicit_path = args[idx + 1]
    else:
        print('ERROR: --path requires a value')
        sys.exit(1)

name_args = [a for a in args if not a.startswith('--') and a != explicit_path]

if not name_args:
    print('Usage: name-session.py "name" [--path /path/to/session.jsonl] [--force]')
    sys.exit(1)

name = name_args[0].strip()

if explicit_path:
    current = Path(explicit_path)
    if not current.exists():
        print(f'ERROR: {explicit_path} not found')
        sys.exit(1)
else:
    mode, data, cwd = get_scope()
    projects_dir = Path.home() / '.claude' / 'projects'

    if mode == 'single':
        cwd_key = data
    elif cwd:
        cwd_key = project_key(cwd, projects_dir)
    else:
        print('ERROR: cannot determine project key')
        sys.exit(1)

    proj_dir = projects_dir / cwd_key
    jsonls = list(proj_dir.glob('*.jsonl'))
    if not jsonls:
        print('ERROR: no session JSONL found')
        sys.exit(1)

    current = max(jsonls, key=lambda f: f.stat().st_mtime)

# Check for existing title
existing = read_title(current)

if existing and not force:
    print(f'Already named: {existing} (use --force to override)')
    sys.exit(0)

try:
    write_title(current, name)
    print(f'Session named: {name}')
except Exception as e:
    print(f'warning: could not write session name: {e}', file=sys.stderr)
    sys.exit(1)
