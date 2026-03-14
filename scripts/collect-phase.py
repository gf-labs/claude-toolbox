#!/usr/bin/env python3
"""Detect a roadmap/phase doc in the current project and extract current phase + blockers."""
import re
from pathlib import Path

CANDIDATES = [
    'docs/todo.md',
    'docs/roadmap.md',
    'ROADMAP.md',
    'docs/ROADMAP.md',
    'TODO.md',
]

cwd = Path.cwd()
doc = None
for c in CANDIDATES:
    p = cwd / c
    if p.exists():
        doc = p
        break

if doc is None:
    print('NOT_FOUND')
    raise SystemExit(0)

text = doc.read_text()

# Look for a current-phase marker: ## Phase N, ## Current, ## Now, ## In Progress
phase_match = re.search(
    r'^##\s+(Phase\s+\d+[^#\n]*|Current[^#\n]*|Now[^#\n]*)',
    text, re.MULTILINE | re.IGNORECASE
)

print(f'SOURCE: {doc.relative_to(cwd)}')
if phase_match:
    print(f'PHASE: {phase_match.group(1).strip()}')
else:
    print('PHASE: (no phase header detected)')

# Look for blockers
blocker_match = re.search(r'(?:blocker|blocked\s+on)[:\s]+([^\n]+)', text, re.IGNORECASE)
if blocker_match:
    print(f'BLOCKER: {blocker_match.group(1).strip()}')
