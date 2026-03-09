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
sid = current.stem

if 'delete-me' in base:
    print(f'Already marked for deletion: {base}')
else:
    new_title = base + '-delete-me'
    record = json.dumps({'type': 'custom-title', 'customTitle': new_title, 'sessionId': sid})
    with open(current, 'a') as fh:
        fh.write(record + '\n')
    print(f'Marked for deletion: {new_title}')

# Clean up associated artifacts immediately
import shutil
cleaned = []
fh_path = Path.home() / '.claude' / 'file-history' / sid
dbg_path = Path.home() / '.claude' / 'debug' / (sid + '.txt')
senv_path = Path.home() / '.claude' / 'session-env' / sid
if fh_path.exists():
    shutil.rmtree(fh_path)
    cleaned.append('file-history')
if dbg_path.exists():
    dbg_path.unlink()
    cleaned.append('debug')
if senv_path.exists():
    shutil.rmtree(senv_path)
    cleaned.append('session-env')
if cleaned:
    print(f'Cleaned artifacts: {', '.join(cleaned)}')
print('JSONL kept — run /cleanup delete-me to remove session history.')
"
