#!/usr/bin/env python3
"""In-repo superpowers docs map — docs/superpowers/{specs,plans}/*.md per project.

Backs the atlas `specs` facet. `_done-`-prefixed files are lifecycle-done; the rest
are live. `--all` forces global scope (how atlas dispatches it); the default follows
ambient scope. `.superpowers/` (the execution ledger) is deliberately not scanned.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects, global_scope  # noqa: E402


def doc_title(path):
    """First '# ' heading (frontmatter-aware); fallback = filename stem."""
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return path.stem
    in_fm = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == '---':
            in_fm = True
            continue
        if in_fm:
            if line.strip() == '---':
                in_fm = False
            continue
        if line.startswith('# '):
            return line[2:].strip().replace('\t', ' ')
    return path.stem


def rows_for(project):
    out = []
    for kind, sub in (('spec', 'specs'), ('plan', 'plans')):
        d = project.path / 'docs' / 'superpowers' / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob('*.md')):
            status = 'done' if f.name.startswith('_done-') else 'live'
            out.append((project.name, kind, status, f.name, doc_title(f)))
    return out


if __name__ == '__main__':
    scope = global_scope() if '--all' in sys.argv[1:] else None
    print('PROJECT\tKIND\tSTATUS\tFILE\tTITLE')
    for pr in sorted(enumerate_projects(scope=scope), key=lambda p: str(p.path)):
        for row in rows_for(pr):
            print('\t'.join(row))
