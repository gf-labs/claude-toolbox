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
    current = _encode(s)                         # current CC: every non-alnum -> '-'
    if projects_dir is None:
        return current
    legacy = s.replace('/', '-')                # older CC: only '/' -> '-'
    for candidate in (current, legacy):
        if (Path(projects_dir) / candidate).is_dir():
            return candidate
    return current


def _encode(s: str) -> str:
    """Forward path->key character map: every non-alphanumeric char becomes '-'.

    This is the *current* Claude Code encoding. project_key applies it; keys on
    disk may also use an older '/'-only encoding, which _key_char_match tolerates.
    """
    return re.sub(r'[^A-Za-z0-9]', '-', s)


def _key_char_match(k: str, r: str) -> bool:
    """True if key char k could encode real-path char r under either CC encoding.

    A '-' in a key may stand for '/', '_', '.', a literal '-', or any other
    non-alphanumeric char (current encoding collapses them all; the legacy
    '/'-only encoding leaves specials like '_' intact — so those match exactly).
    Alphanumerics must match exactly.
    """
    return r == k or (k == '-' and not r.isalnum())


def _reconstruct(key: str, cwd_str: str | None = None) -> Iterator[Path]:
    """Yield every existing dir whose absolute path encodes to this project key.

    project_key() encodes a path by collapsing non-alphanumeric characters to
    '-' — '/' separators and any '-', '_', '.', space inside a component alike
    (the legacy encoding collapsed only '/'). Both are lossy, so a key cannot be
    decoded by string surgery; it must be disambiguated against the filesystem.

    We walk real directories from the root, matching each candidate's full path
    string against the key character-by-character via _key_char_match. A '/', '_',
    '.', or literal '-' in a real name all reconcile against a '-' in the key, so
    disk decides the interpretation. Every fully-matching directory is yielded;
    there can legitimately be more than one.

    cwd_str: if given, only yield paths strictly below this dir; if None, yield
             any existing match (global mode).
    """
    klen = len(key)

    def _prefix_ok(cs: str) -> bool:
        # cs (a real path string) matches the first len(cs) chars of the key.
        return len(cs) <= klen and all(_key_char_match(key[i], cs[i]) for i in range(len(cs)))

    def walk(current: Path) -> Iterator[Path]:
        cs = str(current)
        if not _prefix_ok(cs):
            return
        if len(cs) == klen:
            if cwd_str is None or (cs != cwd_str and cs.startswith(cwd_str + '/')):
                yield current
            return
        try:
            children = list(current.iterdir())
        except OSError:
            return  # unreadable dir -> dead branch, fail safe
        for child in children:
            if child.is_dir():
                yield from walk(child)

    yield from walk(Path('/'))


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
