#!/usr/bin/env python3
"""Session map — one row per session: project, id, title, last-event date.

Backs the atlas `sessions` facet. Distinct from collect-sessions.py (the cleanup
age/size/status inventory): this is the cross-project "what sessions exist and
what are they called" lens. `--all` forces global scope (how atlas dispatches
it); the default follows ambient scope. Rows rank by the scanned last-event
timestamp, NOT file mtime (any write, including a relabel, perturbs mtime).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects, global_scope  # noqa: E402
from session_naming import scan_title_and_ts  # noqa: E402

scope = global_scope() if '--all' in sys.argv[1:] else None
projects = enumerate_projects(scope=scope)

print('PROJECT\tSESSION\tTITLE\tLAST_EVENT')
for pr in sorted(projects, key=lambda p: str(p.path)):
    if not pr.proj_dir.is_dir():
        continue
    rows = []
    for f in sorted(pr.proj_dir.glob('*.jsonl')):  # non-recursive: agent transcripts live in subdirs
        title, ts = scan_title_and_ts(f)
        rows.append((ts, f.stem, title))
    rows.sort(reverse=True)  # ISO timestamps sort lexicographically; stem breaks ties
    for ts, stem, title in rows:
        print(f'{pr.name}\t{stem}\t{title or "—"}\t{ts[:10] if ts else "—"}')
