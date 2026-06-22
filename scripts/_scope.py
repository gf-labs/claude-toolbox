#!/usr/bin/env python3
"""Scope detection: single claude-project, parent roll-up, or global."""
import os
import re
from collections.abc import Iterator
from pathlib import Path


def project_key(path: str | Path, projects_dir: str | Path | None = None) -> str:
    """Encode an absolute filesystem path to its ~/.claude/projects/ dir name.

    Claude Code replaces every non-alphanumeric character in the cwd with '-'.
    That rule has changed over time (older builds replaced only '/'), so the
    same path may have a project dir under more than one encoding on the same
    machine. When projects_dir is given, probe disk and return the encoding that
    exists — current rule first, then the legacy '/'-only fallback — so both
    freshly- and historically-created project dirs resolve. With no projects_dir,
    return the current encoding (what Claude Code creates for a new project).

    This is the forward inverse of _reconstruct; both live here so the
    non-trivial path<->key encoding has exactly one home.
    """
    s = str(path)
    current = re.sub(r'[^A-Za-z0-9]', '-', s)   # current CC: every non-alnum -> '-'
    if projects_dir is None:
        return current
    legacy = s.replace('/', '-')                # older CC: only '/' -> '-'
    for candidate in (current, legacy):
        if (Path(projects_dir) / candidate).is_dir():
            return candidate
    return current


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


def resolve_key(key: str, cwd_str: str | None = None) -> Path | None:
    """Reverse a ~/.claude/projects/ key to its single best existing path.

    Returns the first path _reconstruct yields — the path<->key encoding's
    inverse, disambiguating '-' as a separator vs a literal hyphen against what
    exists on disk — or None if no existing directory matches. Use this wherever
    one owning path is needed; iterate _reconstruct directly for every candidate.
    """
    return next(_reconstruct(key, cwd_str), None)


def get_scope(cwd: str | None = None) -> tuple[str, str | list[tuple[str, Path]], Path | None]:
    """
    Returns one of:
      ('single', project_key: str, cwd: Path)
      ('parent', children: list[tuple[str, Path]], cwd: Path)
      ('global', None, None)
    """
    cwd = Path(cwd or os.getcwd())
    projects_dir = Path.home() / '.claude' / 'projects'

    if not projects_dir.exists():
        return ('global', None, None)

    # Single check first: if cwd is itself a known project, return single regardless
    # of whether it also has descendant projects (running from within a project root).
    cwd_key = project_key(cwd, projects_dir)
    if (projects_dir / cwd_key).exists():
        return ('single', cwd_key, cwd)

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

    return ('global', None, None)


if __name__ == '__main__':
    mode, data, cwd = get_scope()
    if mode == 'single':
        print(f'SINGLE {cwd.name} ({data})')
    elif mode == 'parent':
        print(f'PARENT {cwd} — {len(data)} projects: {[c.name for _, c in data]}')
    else:
        print('GLOBAL')
