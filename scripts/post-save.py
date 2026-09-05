#!/usr/bin/env python3
"""Post-session-save: name current session and rename unnamed sessions in scope.

Called after saving the session log in /tools:pin and /tools:wrap.
No arguments needed — derives name from git commit or first user message,
determines current session by mtime, and handles --skip internally.

Output:
  "Named: <name>"         if current session was unnamed and got a name
  "Renamed: a→x, b→y"    if other unnamed sessions were renamed (omitted if none)
  "NONE"                  if nothing was done
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects
from _scope import get_scope
from _session import current_session_jsonl
from session_index import get_status as _get_registry_status
from session_naming import (
    derive_name,
    extract_context,
    is_junk_title,
    plan_fork_relabels,
    read_title,
    write_title,
)

mode, data, cwd = get_scope()
proj_dirs = sorted((p.proj_dir for p in enumerate_projects((mode, data, cwd))),
                   key=lambda d: d.name)

named_current = ''
renamed = []
relabeled = []

for proj_dir in proj_dirs:
    if not proj_dir.exists():
        continue
    jsonls = sorted(proj_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
    if not jsonls:
        continue

    current = current_session_jsonl(proj_dir)  # env-var authoritative, mtime fallback

    # Name current session if unnamed or junk-titled, and not registry-protected.
    # A junk/scratch title (is_junk_title) is re-derived over; a real name is left
    # alone, and nothing is written unless a real name can be derived, so a
    # session is never blanked.
    cur_title = read_title(current)
    if (not cur_title or is_junk_title(cur_title)) and \
            _get_registry_status(proj_dir.name, current.stem) not in ('done', 'keep'):
        commit, first_user = extract_context(current)
        name = derive_name(commit, first_user)
        if name and name != cur_title:
            write_title(current, name)
            named_current = name

    # Rename other unnamed or junk-titled sessions in this project
    for f in [j for j in jsonls if j != current]:
        f_title = read_title(f)
        if f_title and not is_junk_title(f_title):
            continue
        if _get_registry_status(proj_dir.name, f.stem) in ('done', 'keep'):
            continue
        commit, first_user = extract_context(f)
        if not commit and not first_user:
            continue
        name = derive_name(commit, first_user)
        if not name or name == f_title:
            continue
        write_title(f, name)
        renamed.append(f'{f.stem[:8]}→{name}')

    # Disambiguate same-named forks (compact continuations) in this project.
    # Skipped in global mode — it would full-scan every project's sessions.
    if mode != 'global':
        for a in plan_fork_relabels(proj_dir):
            if write_title(a['path'], a['proposed']):
                relabeled.append(f'{a["sid"]}→{a["proposed"]}')

did_something = False
if named_current:
    print(f'Named: {named_current}')
    did_something = True
if renamed:
    print(f'Renamed: {", ".join(renamed)}')
    did_something = True
if relabeled:
    print(f'Relabeled forks: {", ".join(relabeled)}')
    did_something = True
if not did_something:
    print('NONE')
