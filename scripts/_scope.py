#!/usr/bin/env python3
"""Scope detection: single claude-project, parent roll-up, or global."""
import os
from collections.abc import Iterator
from pathlib import Path


def _reconstruct(key: str, cwd_str: str | None = None) -> Iterator[Path]:
    """Yield all existing dirs that could match this project key.

    Project keys encode paths as '-'-joined components, but directory names
    may also contain hyphens, making naive replacement ambiguous. This function
    backtracks: at each '-', it tries treating it as a path separator OR as a
    literal hyphen in the current directory name.

    Pruning: when trying a path separator, we only recurse if the path built
    so far is an existing directory — this eliminates bad branches early.

    cwd_str: if given, only yield paths that are descendants of this dir.
             If None, yield any existing directory (global mode).
    """
    parts = key.lstrip('-').split('-')

    def build(idx, path_parts):
        if idx == len(parts):
            p = Path('/' + '/'.join(path_parts))
            if not p.is_dir():
                return
            p_str = str(p)
            if cwd_str is None or (p_str != cwd_str and p_str.startswith(cwd_str + '/')):
                yield p
            return
        part = parts[idx]
        # Option A: new path component — prune if current path doesn't exist
        current = Path('/' + '/'.join(path_parts))
        if current.is_dir():
            yield from build(idx + 1, path_parts + [part])
        # Option B: extend current component with hyphen (always try)
        if path_parts:
            yield from build(idx + 1, path_parts[:-1] + [path_parts[-1] + '-' + part])

    yield from build(1, [parts[0]])


def get_scope(cwd: str | None = None) -> tuple[str, str | list[tuple[str, Path]], Path | None]:
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

    # Find all known projects that are descendants of cwd (any depth)
    seen = set()
    descendants = []
    cwd_str = str(cwd)
    for proj_dir in sorted(projects_dir.iterdir()):
        if not proj_dir.is_dir():
            continue
        for reconstructed in _reconstruct(proj_dir.name, cwd_str):
            if reconstructed not in seen:
                seen.add(reconstructed)
                descendants.append((proj_dir.name, reconstructed))

    if descendants:
        return ('parent', descendants, cwd)

    if (projects_dir / cwd_key).exists():
        return ('single', cwd_key, cwd)

    return ('global', None, None)


if __name__ == '__main__':
    mode, data, cwd = get_scope()
    if mode == 'single':
        print(f'SINGLE {cwd.name} ({data})')
    elif mode == 'parent':
        print(f'PARENT {cwd} — {len(data)} projects: {[c.name for _, c in data]}')
    else:
        print('GLOBAL')
