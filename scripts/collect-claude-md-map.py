#!/usr/bin/env python3
"""CLAUDE.md inheritance MAP + MEMORY status per in-scope project (the map, not analysis).

Emits which CLAUDE.md files Claude Code inherits for each project (global -> project)
plus MEMORY.md size/flag. Dedup / conflict / CLAUDE.md-x-MEMORY analysis is deliberately out of scope here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects, global_scope  # noqa: E402


def memory_status(mem_file):
    """(lines_str, status) — same thresholds as collect-status."""
    if not mem_file.exists():
        return 'none', 'MISSING'
    n = len(mem_file.read_text(encoding='utf-8').splitlines())
    status = 'WARN' if n >= 150 else ('OK' if n >= 50 else 'THIN')
    return f'{n}L', status


def claude_md_chain(project_path, home):
    """~-relative CLAUDE.md paths Claude Code inherits, general -> specific.

    Global ~/.claude/CLAUDE.md first, then each ancestor dir from home down to the
    project that has a CLAUDE.md. Only ancestors under home are considered.
    """
    chain = []
    if (home / '.claude' / 'CLAUDE.md').exists():
        chain.append('~/.claude/CLAUDE.md')
    ancestors = []
    p = project_path
    while True:
        ancestors.append(p)
        if p == home or p.parent == p:
            break
        p = p.parent
    for a in reversed(ancestors):
        try:
            rel = a.relative_to(home)
        except ValueError:
            continue  # not under home
        if (a / 'CLAUDE.md').exists():
            rel_cm = 'CLAUDE.md' if str(rel) == '.' else f'{rel}/CLAUDE.md'
            chain.append(f'~/{rel_cm}')
    return chain


def build_rows(projects, home):
    rows = []
    for pr in projects:
        chain = claude_md_chain(pr.path, home)
        mem_lines, mem_stat = memory_status(pr.proj_dir / 'memory' / 'MEMORY.md')
        rows.append((pr.container or '', pr.name, str(len(chain)),
                     mem_lines, mem_stat, ' » '.join(chain) if chain else '(none)'))
    return rows


if __name__ == '__main__':
    home = Path.home()
    scope = global_scope() if '--all' in sys.argv[1:] else None
    print('CONTAINER\tPROJECT\tCLAUDE_MD_DEPTH\tMEMORY_LINES\tMEMORY_STATUS\tCHAIN')
    for row in build_rows(enumerate_projects(scope=scope), home):
        print('\t'.join(row))
