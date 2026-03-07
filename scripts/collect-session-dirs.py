#!/usr/bin/env python3
"""Session directories (tool-results, subagents) for OLD sessions."""
import argparse, time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

found = False
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
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
