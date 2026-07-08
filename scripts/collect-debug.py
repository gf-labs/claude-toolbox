#!/usr/bin/env python3
"""Debug logs for OLD sessions."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

debug_dir = Path.home() / '.claude' / 'debug'
cutoff = time.time() - args.days * 86400

if not debug_dir.exists():
    print('NONE')
else:
    old_sessions = set()
    for p in enumerate_projects():
        for f in p.proj_dir.iterdir():
            if f.name.endswith('.jsonl') and f.stat().st_mtime < cutoff:
                old_sessions.add(f.stem)
    found = False
    for f in sorted(debug_dir.iterdir()):
        if f.stem in old_sessions:
            print(f'debug/{f.name}  {f.stat().st_size // 1024}K  OLD')
            found = True
    if not found:
        print('none')
