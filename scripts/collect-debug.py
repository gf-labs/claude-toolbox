#!/usr/bin/env python3
"""Debug logs for OLD sessions."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

debug_dir = Path.home() / '.claude' / 'debug'
projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

_mode, _scope_data, _scope_cwd = get_scope()
if _mode == 'single':
    allowed_keys = {_scope_data}
elif _mode == 'parent':
    allowed_keys = {k for k, _ in _scope_data}
else:
    allowed_keys = None

if not debug_dir.exists():
    print('NONE')
else:
    old_sessions = set()
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        if allowed_keys is not None and proj.name not in allowed_keys:
            continue
        for f in proj.iterdir():
            if f.name.endswith('.jsonl') and f.stat().st_mtime < cutoff:
                old_sessions.add(f.stem)
    found = False
    for f in sorted(debug_dir.iterdir()):
        if f.stem in old_sessions:
            print(f'debug/{f.name}  {f.stat().st_size // 1024}K  OLD')
            found = True
    if not found:
        print('none')
