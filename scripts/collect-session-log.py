#!/usr/bin/env python3
"""Session log metadata and recent entries per project."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

MAX_ENTRIES = 5
MAX_ENTRY_LEN = 90


def _log_info(proj_dir):
    """Return (last_log_date, entry_count, recent_entries) from session-log.md."""
    log_file = proj_dir / 'memory' / 'session-log.md'
    if not log_file.exists():
        return '—', '—', []
    text = log_file.read_text(encoding='utf-8')
    dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if not dates:
        return '—', '—', []

    # Extract bullets from the last (most recent) session block
    blocks = re.split(r'^## ', text, flags=re.MULTILINE)
    last_block = blocks[-1] if blocks else ''
    entries = []
    for line in last_block.splitlines():
        line = line.strip()
        if line.startswith('- '):
            entry = line[2:].strip()
            if len(entry) > MAX_ENTRY_LEN:
                entry = entry[:MAX_ENTRY_LEN - 1] + '…'
            entries.append(entry)
        if len(entries) >= MAX_ENTRIES:
            break

    return dates[-1], str(len(dates)), entries


mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    cwd_key = data
    last_log, count, entries = _log_info(projects_dir / cwd_key)
    print(f'SINGLE {cwd}')
    print(f'LAST_SESSION_LOG\t{last_log}\tLOG_ENTRIES\t{count}')
    if entries:
        print('RECENT_ENTRIES:')
        for e in entries:
            print(f'  - {e}')
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

entries_blocks = []
for name, path in projects:
    cwd_key = str(path).replace('/', '-')
    last_log, count, entries = _log_info(projects_dir / cwd_key)
    print(f'{name}\t{last_log}\t{count}')
    if entries:
        entries_blocks.append((name, last_log, entries))

if entries_blocks:
    print()
    # Sort by date descending — show most recent project first
    entries_blocks.sort(key=lambda x: x[1], reverse=True)
    for name, last_log, entries in entries_blocks:
        print(f'ENTRIES:{name}\t{last_log}')
        for e in entries:
            print(f'  - {e}')
