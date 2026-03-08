#!/usr/bin/env python3
"""Scope detection: single claude-project, parent roll-up, or global."""
import os
from pathlib import Path


def get_scope(cwd=None):
    """
    Returns one of:
      ('single', project_key: str, cwd: Path)
      ('parent', children: list[tuple[str, Path]], cwd: Path)
      ('global', None, None)
    """
    cwd = Path(cwd or os.getcwd())
    cwd_key = str(cwd).replace('/', '-')
    projects_dir = Path.home() / '.claude' / 'projects'

    if not projects_dir.exists():
        return ('global', None, None)

    if (projects_dir / cwd_key).exists():
        return ('single', cwd_key, cwd)

    children = []
    try:
        for child in sorted(cwd.iterdir()):
            if not child.is_dir():
                continue
            child_key = str(child).replace('/', '-')
            if (projects_dir / child_key).exists():
                children.append((child_key, child))
    except PermissionError:
        pass

    if children:
        return ('parent', children, cwd)

    return ('global', None, None)


if __name__ == '__main__':
    mode, data, cwd = get_scope()
    if mode == 'single':
        print(f'SINGLE {cwd.name} ({data})')
    elif mode == 'parent':
        print(f'PARENT {cwd} — {len(data)} projects: {[c.name for _, c in data]}')
    else:
        print('GLOBAL')
