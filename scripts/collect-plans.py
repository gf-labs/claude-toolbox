#!/usr/bin/env python3
"""Plans inventory."""
from pathlib import Path

plans_dir = Path.home() / '.claude' / 'plans'
if not plans_dir.exists() or not list(plans_dir.glob('*.md')):
    print('NONE')
else:
    for f in sorted(plans_dir.glob('*.md')):
        lines = len(f.read_text().splitlines())
        title = ''
        for line in f.read_text().splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                break
        print(f'{f.name}  {lines}L  {title[:60]}')
