#!/usr/bin/env python3
"""Write a custom-title record to the current session JSONL.

Usage: python3 name-session.py "short-name-here" [--force]
Skips silently if session already has a custom-title (unless --force).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

args = sys.argv[1:]
force = '--force' in args
name_args = [a for a in args if not a.startswith('--')]

if not name_args:
    print('Usage: name-session.py "name" [--force]')
    sys.exit(1)

name = name_args[0].strip()

mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    cwd_key = data
elif cwd:
    cwd_key = str(cwd).replace('/', '-')
else:
    print('ERROR: cannot determine project key')
    sys.exit(1)

proj_dir = projects_dir / cwd_key
jsonls = list(proj_dir.glob('*.jsonl'))
if not jsonls:
    print('ERROR: no session JSONL found')
    sys.exit(1)

current = max(jsonls, key=lambda f: f.stat().st_mtime)
sid = current.stem

# Check for existing title
existing = ''
for line in current.read_text(errors='replace').splitlines():
    try:
        obj = json.loads(line)
        if obj.get('type') == 'custom-title':
            existing = obj.get('customTitle', '')
    except Exception:
        pass

if existing and not force:
    print(f'Already named: {existing} (use --force to override)')
    sys.exit(0)

record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': sid})
with open(current, 'a') as fh:
    fh.write(record + '\n')
print(f'Session named: {name}')
