#!/usr/bin/env python3
"""Mark the current session for deletion and clean up associated artifacts."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_index import get_status, set_status
from session_naming import write_title

parser = argparse.ArgumentParser(description='Mark current session done or keep.')
parser.add_argument('--keep', action='store_true',
                    help='Mark as keep (retain JSONL, skip deletion)')
parser.add_argument('--force', action='store_true',
                    help='Override an existing done/keep status')
parser.add_argument('--reason', default='',
                    help='Reason for --force override (audit trail)')
args = parser.parse_args()

projects_dir = Path.home() / '.claude' / 'projects'
mode, data, cwd = get_scope()

if mode == 'single':
    proj_dir = projects_dir / data
else:
    try:
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        proj_dir = projects_dir / git_root.replace('/', '-')
    except Exception:
        print('ERROR: Could not determine project key', file=sys.stderr)
        sys.exit(1)

jsonl_files = list(proj_dir.glob('*.jsonl'))
if not jsonl_files:
    print(f'ERROR: No session files found in {proj_dir}', file=sys.stderr)
    sys.exit(1)

current = max(jsonl_files, key=lambda f: f.stat().st_mtime)
project_key = proj_dir.name
sid = current.stem

last_title = ''
first_slug = ''
for line in current.read_text(errors='replace').splitlines():
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('type') == 'custom-title':
        last_title = obj.get('customTitle', '')
    if not first_slug and obj.get('slug'):
        first_slug = obj['slug']

base = last_title or first_slug or current.stem[:8]
new_status = 'keep' if args.keep else 'done'
existing_status = get_status(project_key, sid)

if existing_status in ('done', 'keep') and not args.force:
    print(f'Already {existing_status}: {base} — use --force to override')
    sys.exit(0)

# Write JSONL custom-title (backward compatibility)
if 'delete-me' not in base:
    new_title = base + '-delete-me'
    write_title(current, new_title)
    print(f'Marked for deletion: {new_title}')
else:
    print(f'Already marked: {base}')

# Write registry (authoritative)
now = datetime.now(timezone.utc).isoformat()
kwargs: dict = {'name': base, 'done_at': now}
if args.force and existing_status:
    kwargs['forced_at'] = now
    kwargs['forced_reason'] = args.reason or '(no reason given)'
set_status(project_key, sid, new_status, **kwargs)

# Clean up associated artifacts
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
    print(f'Cleaned artifacts: {", ".join(cleaned)}')
