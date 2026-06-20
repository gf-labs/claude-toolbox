#!/usr/bin/env python3
"""Memory health and size warnings per project (merged view)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

projects_dir = Path.home() / '.claude' / 'projects'

_mode, _scope_data, _scope_cwd = get_scope()
if _mode == 'single':
    allowed_keys = {_scope_data}
elif _mode == 'parent':
    allowed_keys = {k for k, _ in _scope_data}
else:
    allowed_keys = None

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
        continue
    if allowed_keys is not None and proj.name not in allowed_keys:
        continue
    mem = proj / 'memory' / 'MEMORY.md'
    if mem.exists():
        lines = len(mem.read_text(encoding='utf-8').splitlines())
        if lines >= 150:
            status = 'WARN:NEAR-LIMIT'
        elif lines >= 50:
            status = 'OK'
        else:
            status = 'THIN'
        print(f'{proj.name}  {lines}L  {status}')
    else:
        print(f'{proj.name}  NO MEMORY.md  MISSING')
