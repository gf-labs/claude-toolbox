#!/usr/bin/env python3
"""Session directories (tool-results, subagents) for OLD sessions."""
import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

_mode, _scope_data, _scope_cwd = get_scope()
if _mode == 'single':
    allowed_keys = {_scope_data}
elif _mode == 'parent':
    allowed_keys = {k for k, _ in _scope_data}
else:
    allowed_keys = None

found = False
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
        continue
    if allowed_keys is not None and proj.name not in allowed_keys:
        continue
    for entry in sorted(proj.iterdir()):
        if not entry.is_dir() or entry.name == 'memory':
            continue
        jsonl = proj / (entry.name + '.jsonl')
        if jsonl.exists() and jsonl.stat().st_mtime < cutoff:
            size = sum(f.stat().st_size for f in entry.rglob('*') if f.is_file())
            print(f'{proj.name}  {entry.name}/  {size // 1024}K  OLD-DIR')
            found = True

if not found:
    print('none')
