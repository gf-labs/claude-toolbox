#!/usr/bin/env python3
"""Session inventory — age, size, OLD/KEEP/ARTIFACT status."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_index import read_registry
from session_naming import read_title

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

_mode, _scope_data, _scope_cwd = get_scope()
if _mode == 'single':
    allowed_keys = {_scope_data}
elif _mode == 'parent':
    allowed_keys = {k for k, _ in _scope_data}
else:
    allowed_keys = None

ARTIFACT_TYPES = {'file-history-snapshot'}
CONVERSATION_TYPES = {
    'user', 'assistant', 'progress', 'system', 'custom-title',
    'last-prompt', 'queue-operation', 'summary',
}


def is_artifact_only(path):
    try:
        for line in path.read_text().splitlines():
            obj = json.loads(line)
            t = obj.get('type', '')
            if t in CONVERSATION_TYPES:
                return False
            if t not in ARTIFACT_TYPES:
                return False
        return True
    except Exception:
        return False


if not projects_dir.exists():
    print('NO PROJECTS DIR')
else:
    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir():
            continue
        if allowed_keys is not None and proj.name not in allowed_keys:
            continue
        registry = read_registry(proj.name)
        for f in sorted(proj.iterdir()):
            if not f.name.endswith('.jsonl'):
                continue
            try:
                stat = f.stat()
                age = (time.time() - stat.st_mtime) / 86400
                custom_title = read_title(f)
                reg_entry = registry.get(f.stem, {})
                reg_status = reg_entry.get('status')
                if reg_status == 'artifact':
                    status = 'ARTIFACT'
                elif reg_status == 'done':
                    status = 'DELETE-ME'
                elif reg_status == 'keep':
                    status = 'KEEP'
                else:
                    # Fallback: JSONL scan for sessions not yet in registry
                    if is_artifact_only(f):
                        status = 'ARTIFACT'
                    elif 'delete-me' in custom_title.lower():
                        status = 'DELETE-ME'
                    else:
                        status = 'OLD' if stat.st_mtime < cutoff else 'KEEP'
                label = f'  title={custom_title!r}' if custom_title else ''
                print(f'{proj.name}  {f.stem}  {age:.0f}d  {stat.st_size // 1024}K  {status}{label}')
            except Exception as e:
                print(f'ERROR: {f} — {e}')
