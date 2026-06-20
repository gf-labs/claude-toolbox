#!/usr/bin/env python3
"""One-time backfill: scan JSONL files and initialize sessions-meta.json.
Idempotent — skips sessions already in the registry.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_index import get_status, set_status
from session_naming import read_title

CONVERSATION_TYPES = {
    'user', 'assistant', 'progress', 'system',
    'last-prompt', 'queue-operation', 'summary',
}


def _is_artifact(path: Path) -> bool:
    """True if JSONL has no human conversation turns."""
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get('type') in CONVERSATION_TYPES:
                return False
        return True
    except OSError:
        return False


if __name__ == '__main__':
    projects_dir = Path.home() / '.claude' / 'projects'
    mode, data, cwd = get_scope()

    if mode == 'single':
        allowed_keys = {data}
    elif mode == 'parent':
        allowed_keys = {k for k, _ in data}
    else:
        allowed_keys = None  # global — scan all

    done_count = 0
    artifact_count = 0
    skipped_count = 0

    if not projects_dir.exists():
        print('No projects directory found.')
        sys.exit(0)

    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir():
            continue
        if allowed_keys is not None and proj.name not in allowed_keys:
            continue
        project_key = proj.name
        for f in sorted(proj.glob('*.jsonl')):
            uuid = f.stem
            if get_status(project_key, uuid) is not None:
                skipped_count += 1
                continue
            title = read_title(f)
            if 'delete-me' in title.lower():
                # Strip delete-me marker (prefix, suffix, or standalone)
                name = re.sub(r'(?:^delete-me-|-delete-me$|^delete-me$)', '', title.lower()).strip('-')
                if not name:
                    name = f.stem[:8]  # fallback to UUID prefix
                set_status(project_key, uuid, 'done', name=name)
                done_count += 1
            elif _is_artifact(f):
                set_status(project_key, uuid, 'artifact')
                artifact_count += 1

    print(f'Migrated: {done_count} done, {artifact_count} artifact, {skipped_count} skipped (already indexed)')
