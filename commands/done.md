---
description: Mark this session for deletion — appends delete-me to the custom title, picked up by /cleanup delete-me
allowed-tools: Bash
---

Mark the current session for deletion by appending a `custom-title` record to the active session JSONL. Sessions with "delete-me" in their title are matched by `/cleanup delete-me`.

!python3 -c "
import json, os
from pathlib import Path

cwd = os.getcwd()
proj_key = cwd.replace('/', '-')
proj_dir = Path.home() / '.claude' / 'projects' / proj_key

jsonl_files = list(proj_dir.glob('*.jsonl'))
if not jsonl_files:
    print('ERROR: No session files found in', proj_dir)
    exit(1)

current = max(jsonl_files, key=lambda f: f.stat().st_mtime)

# Read last custom-title and first slug as fallback
last_title = ''
first_slug = ''
for line in current.read_text(errors='replace').splitlines():
    if not line.strip(): continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('type') == 'custom-title':
        last_title = obj.get('customTitle', '')
    if not first_slug and obj.get('slug'):
        first_slug = obj['slug']

base = last_title or first_slug or current.stem[:8]

if 'delete-me' in base:
    print(f'Already marked for deletion: {base}')
else:
    new_title = base + '-delete-me'
    record = json.dumps({'type': 'custom-title', 'customTitle': new_title, 'sessionId': current.stem})
    with open(current, 'a') as f:
        f.write(record + '\n')
    print(f'Marked for deletion: {new_title}')
    print('Run /cleanup delete-me to clean up.')
"
