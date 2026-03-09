#!/usr/bin/env python3
"""Session log metadata — last date and entry count per project."""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope


def _log_info(proj_dir):
    """Return (last_log_date, entry_count) from session-log.md."""
    log_file = proj_dir / 'memory' / 'session-log.md'
    if not log_file.exists():
        return '—', '—'
    text = log_file.read_text()
    dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if not dates:
        return '—', '—'
    return dates[-1], str(len(dates))


mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    cwd_key = data
    last_log, count = _log_info(projects_dir / cwd_key)
    print(f'SINGLE {cwd}')
    print(f'LAST_SESSION_LOG\t{last_log}\tLOG_ENTRIES\t{count}')
    sys.exit(0)

if mode == 'parent':
    projects = [(c.name, c) for _, c in data]
else:
    projects = []
    for proj_key in sorted(projects_dir.iterdir()):
        if not proj_key.is_dir():
            continue
        reconstructed = Path('/' + proj_key.name[1:].replace('-', '/'))
        if reconstructed.is_dir():
            projects.append((reconstructed.name, reconstructed))

print('PROJECT\tLAST_LOG\tLOG_ENTRIES')

for name, path in projects:
    cwd_key = str(path).replace('/', '-')
    last_log, count = _log_info(projects_dir / cwd_key)
    print(f'{name}\t{last_log}\t{count}')
