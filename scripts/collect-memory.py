#!/usr/bin/env python3
"""Memory health and size warnings per project (merged view)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects

for p in sorted(enumerate_projects(), key=lambda x: x.key):
    mem = p.proj_dir / 'memory' / 'MEMORY.md'
    if mem.exists():
        lines = len(mem.read_text(encoding='utf-8').splitlines())
        if lines >= 150:
            status = 'WARN:NEAR-LIMIT'
        elif lines >= 50:
            status = 'OK'
        else:
            status = 'THIN'
        print(f'{p.key}  {lines}L  {status}')
    else:
        print(f'{p.key}  NO MEMORY.md  MISSING')
