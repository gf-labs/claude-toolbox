#!/usr/bin/env python3
"""Session directories (tool-results, subagents) for OLD sessions."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

cutoff = time.time() - args.days * 86400

found = False
for p in sorted(enumerate_projects(), key=lambda x: x.key):
    for entry in sorted(p.proj_dir.iterdir()):
        if not entry.is_dir() or entry.name == 'memory':
            continue
        jsonl = p.proj_dir / (entry.name + '.jsonl')
        if jsonl.exists() and jsonl.stat().st_mtime < cutoff:
            size = sum(f.stat().st_size for f in entry.rglob('*') if f.is_file())
            print(f'{p.key}  {entry.name}/  {size // 1024}K  OLD-DIR')
            found = True

if not found:
    print('none')
