#!/usr/bin/env python3
"""File-history directories for OLD sessions."""
import argparse, time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

fh_dir = Path.home() / '.claude' / 'file-history'
projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

if not fh_dir.exists():
    print('NONE')
else:
    old_sessions = set()
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        for f in proj.iterdir():
            if f.name.endswith('.jsonl') and f.stat().st_mtime < cutoff:
                old_sessions.add(f.stem)
    found = False
    for session_dir in sorted(fh_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        if session_dir.name in old_sessions:
            size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
            print(f'file-history/{session_dir.name}  {size // 1024}K  OLD')
            found = True
    if not found:
        print('none')
