#!/usr/bin/env python3
"""Session inventory — age, size, OLD/KEEP/ARTIFACT status."""
import argparse, json, time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=30)
args, _ = parser.parse_known_args()

projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - args.days * 86400

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
        for f in sorted(proj.iterdir()):
            if not f.name.endswith('.jsonl'):
                continue
            try:
                stat = f.stat()
                age = (time.time() - stat.st_mtime) / 86400
                custom_title = ''
                try:
                    for line in f.read_text(errors='replace').splitlines():
                        obj = json.loads(line)
                        if obj.get('type') == 'custom-title':
                            custom_title = obj.get('customTitle', '')
                            break
                except Exception:
                    pass
                if is_artifact_only(f):
                    status = 'ARTIFACT'
                else:
                    status = 'OLD' if stat.st_mtime < cutoff else 'KEEP'
                label = f'  title={custom_title!r}' if custom_title else ''
                print(f'{proj.name}  {f.stem}  {age:.0f}d  {stat.st_size // 1024}K  {status}{label}')
            except Exception as e:
                print(f'ERROR: {f} — {e}')
