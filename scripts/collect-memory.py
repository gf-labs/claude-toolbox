#!/usr/bin/env python3
"""Memory health and size warnings per project (merged view)."""
from pathlib import Path

projects_dir = Path.home() / '.claude' / 'projects'

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
        continue
    mem = proj / 'memory' / 'MEMORY.md'
    if mem.exists():
        lines = len(mem.read_text().splitlines())
        if lines >= 150:
            status = 'WARN:NEAR-LIMIT'
        elif lines >= 50:
            status = 'OK'
        else:
            status = 'THIN'
        print(f'{proj.name}  {lines}L  {status}')
    else:
        print(f'{proj.name}  NO MEMORY.md  MISSING')
