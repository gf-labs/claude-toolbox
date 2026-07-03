#!/usr/bin/env python3
"""Pure render layer for the atlas ATLAS section: collector text -> final human text.

No I/O, no subprocess — collect-atlas.py dispatches the collectors and hands their
stdout here, so every function is testable on canned strings. build_atlas() is the
entry point: digest (one aligned line per project, grouped) at scale, cards
(per-project resource blocks) when the scope is small.
"""
import datetime
import os
import re
from pathlib import Path


def elapsed(date_str, today):
    """'YYYY-MM-DD' -> 'today' | 'yesterday' | 'Nd ago'; unparseable -> '—'.

    Future dates clamp to 'today' — session timestamps are UTC-truncated and can
    land a calendar day ahead of local time.
    """
    try:
        d = datetime.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return '—'
    days = (today - d).days
    if days <= 0:
        return 'today'
    if days == 1:
        return 'yesterday'
    return f'{days}d ago'


def shorten_chain(chain):
    """' » '-joined ~/…/CLAUDE.md paths -> ' » '-joined directory basenames.

    '~/.claude/CLAUDE.md' -> 'global'; a home-level '~/CLAUDE.md' -> '~'.
    """
    parts = []
    for element in chain.split(' » '):
        e = element.strip()
        if e == '~/.claude/CLAUDE.md':
            parts.append('global')
            continue
        parent = e[:-len('/CLAUDE.md')] if e.endswith('/CLAUDE.md') else e
        parts.append('~' if parent in ('~', '') else parent.rsplit('/', 1)[-1])
    return ' » '.join(parts)


def parse_status(text):
    """collect-status TSV -> {PROJECT: [row-dict, ...]} (list — duplicate basenames).

    Rows shorter than the header (pre-LAST_COMMIT_DATE output) simply lack the
    trailing keys. The '# ORPHANED/UNSCOPED' tail is --stale's business, not ours.
    """
    rows = {}
    fields = None
    for line in text.splitlines():
        if line.startswith('# '):
            break
        if not line.strip():
            continue
        if line.startswith('GROUP\t'):
            fields = line.split('\t')
            continue
        if fields is None:
            continue
        row = dict(zip(fields, line.split('\t'), strict=False))
        if 'PROJECT' in row:
            rows.setdefault(row['PROJECT'], []).append(row)
    return rows


def status_for(project, status_rows):
    """Pick the status row for a Project; GROUP == its container disambiguates dupes."""
    cands = status_rows.get(project.name, [])
    if len(cands) > 1:
        want = project.container or ''
        for r in cands:
            if r.get('GROUP') in (want, 'header'):
                return r
    return cands[0] if cands else None


def parse_sessions(text):
    """collect-session-list TSV -> {PROJECT: [(session, title, last_event), ...]}.

    Row order (newest-first per project) is the collector's contract — preserved.
    """
    rows = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith('PROJECT\t'):
            continue
        vals = line.split('\t')
        if len(vals) == 4:
            proj_name, sid, title, last = vals
            rows.setdefault(proj_name, []).append((sid, title, last))
    return rows


def parse_claude_md(text):
    """collect-claude-md-map TSV -> {PROJECT: row-dict}."""
    rows = {}
    fields = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith('CONTAINER\t'):
            fields = line.split('\t')
            continue
        if fields is None:
            continue
        vals = line.split('\t')
        if len(vals) == len(fields):
            row = dict(zip(fields, vals, strict=True))
            rows[row['PROJECT']] = row
    return rows


_PLAN_RE = re.compile(r'^(\S+)\s+(\d+)L\s+\[([^\]]*)\]\s*(.*)$')


def parse_plans(text):
    """collect-plans lines -> {project: [(title, 'NL'), ...]}.

    Drops '?' attribution (can't join a project) and '_done-' files (lifecycle-done,
    same convention as the specs facet). '→' detail lines and 'NONE' don't match.
    """
    rows = {}
    for line in text.splitlines():
        m = _PLAN_RE.match(line)
        if not m:
            continue
        fname, nl, project, title = m.groups()
        if project == '?' or fname.startswith('_done-'):
            continue
        fallback = fname[:-3] if fname.endswith('.md') else fname
        rows.setdefault(project, []).append((title or fallback, f'{nl}L'))
    return rows


def parse_specs(text):
    """collect-superpowers-docs TSV -> {PROJECT: [(kind, status, title), ...]}."""
    rows = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith('PROJECT\t'):
            continue
        vals = line.split('\t')
        if len(vals) == 5:
            proj_name, kind, status, _fname, title = vals
            rows.setdefault(proj_name, []).append((kind, status, title))
    return rows


def _truncate(s, n):
    return s if len(s) <= n else s[:n - 1] + '…'


def _grouped_rows(projects):
    """[(group|None, rel_name, Project)] — group = first component under the common root.

    Bare rows (the root project itself, or a direct child — a single-row group is
    noise) come first; groups follow alphabetically, rows sorted by rel_name.
    """
    root = Path(os.path.commonpath([str(p.path) for p in projects]))
    bare, groups = [], {}
    for p in projects:
        if p.path == root:
            bare.append((None, p.name, p))
            continue
        parts = p.path.relative_to(root).parts
        if len(parts) == 1:
            bare.append((None, parts[0], p))
        else:
            groups.setdefault(parts[0], []).append((parts[0], '/'.join(parts[1:]), p))
    out = sorted(bare, key=lambda r: r[1])
    for g in sorted(groups):
        out.extend(sorted(groups[g], key=lambda r: r[1]))
    return out


def _git_cell(st, today):
    if st is None or st.get('BRANCH', '—') == '—':
        return '—'
    changes = st.get('CHANGES', '—')
    branch = _truncate(st['BRANCH'], 22) + (f' ±{changes}' if changes != '—' else '')
    return f"{branch} · {elapsed(st.get('LAST_COMMIT_DATE', '—'), today)}"


def _sessions_cell(sess_rows, today):
    if not sess_rows:
        return '—'
    return f'{len(sess_rows)}s · {elapsed(sess_rows[0][2], today)}'


def _memory_cell(st):
    if st is None or st.get('MEMORY_STATUS', 'MISSING') == 'MISSING':
        return '—'
    return f"{st['MEMORY_LINES']} {st['MEMORY_STATUS']}"


def _docs_cell(project_name, facets, parsed):
    parts = []
    if 'specs' in facets:
        live = sum(1 for _, s, _ in parsed.get('specs', {}).get(project_name, []) if s == 'live')
        if live:
            parts.append(f'{live} spec{"" if live == 1 else "s"}')
    if 'plans' in facets:
        n = len(parsed.get('plans', {}).get(project_name, []))
        if n:
            parts.append(f'{n} plan{"" if n == 1 else "s"}')
    return ' · '.join(parts) or '—'


def _render_digest(projects, facets, parsed, today):
    table = []
    for g, rel, p in _grouped_rows(projects):
        st = status_for(p, parsed.get('status', {}))
        marker = ' !' if st is not None and st.get('CHANGES', '—') != '—' else ''
        cells = [_truncate(rel, 34) + marker]
        if 'projects' in facets:
            cells.append(_git_cell(st, today))
        if 'sessions' in facets:
            cells.append(_sessions_cell(parsed.get('sessions', {}).get(p.name, []), today))
        if 'memory' in facets:
            cells.append(_memory_cell(st))
        if 'plans' in facets or 'specs' in facets:
            cells.append(_docs_cell(p.name, facets, parsed))
        table.append((g, cells))
    widths = [max(len(row[1][i]) for row in table) for i in range(len(table[0][1]))]
    lines, seen_group = [], object()
    for g, cells in table:
        if g != seen_group:
            if g is not None:
                lines.append(f'{g}/')
            seen_group = g
        row = '  '.join(c.ljust(w) for c, w in zip(cells, widths, strict=True)).rstrip()
        lines.append(f'  {row}' if g is not None else row)
    return lines


def _mode(depth, n):
    if depth == 'full':
        return 'cards'
    if depth == 'compact':
        return 'digest'
    return 'cards' if n <= 4 else 'digest'


def _card_header(st, want_git, today):
    parts = []
    if want_git:
        if st is None or st.get('BRANCH', '—') == '—':
            parts.append('(no git)')
        else:
            n = st.get('CHANGES', '—')
            chg = 'clean' if n == '—' else f"{n} change{'' if n == '1' else 's'}"
            parts.append(f"{st['BRANCH']} · {chg} · commit "
                         f"{elapsed(st.get('LAST_COMMIT_DATE', '—'), today)}")
    if st is not None and st.get('BACKLOG_ITEMS', '—') != '—':
        parts.append(f"backlog {st['BACKLOG_ITEMS']}")
    return ' · '.join(parts)


def _card_line(label, detail):
    return f'  {label:<12}{detail}'


def _claude_md_detail(row):
    if row is None or row.get('CHAIN', '(none)') == '(none)':
        return '(none)'
    return f"{shorten_chain(row['CHAIN'])} (depth {row['CLAUDE_MD_DEPTH']})"


def _memory_detail(st, today):
    if st is None or st.get('MEMORY_STATUS', 'MISSING') == 'MISSING':
        return '(none)'
    return (f"{st['MEMORY_LINES']} {st['MEMORY_STATUS']}"
            f" · snapshot {elapsed(st.get('LAST_SNAPSHOT', '—'), today)}"
            f" · log {elapsed(st.get('LAST_SESSION_LOG', '—'), today)}"
            f" ({st.get('LOG_ENTRIES', '—')} entries)")


def _sessions_detail(rows, today, full):
    if not rows:
        return '(none)'
    shown = rows if full else rows[:5]
    parts = [f"{_truncate(title, 24) if title != '—' else sid[:8]} ({elapsed(d, today)})"
             for sid, title, d in shown]
    detail = f'{len(rows)} — ' + ' · '.join(parts)
    if len(rows) > len(shown):
        detail += f' · +{len(rows) - len(shown)} more'
    return detail


def _plans_detail(entries):
    if not entries:
        return '(none)'
    return ' · '.join(f'{title} ({nl})' for title, nl in entries)


def _specs_detail(entries, full):
    """'N live · M done' by default; titles appended only on --full (they're long
    design-doc names that collide once truncated — counts are the scannable signal)."""
    if not entries:
        return '(none)'
    live = [t for _, s, t in entries if s == 'live']
    done = sum(1 for _, s, _ in entries if s == 'done')
    out = f'{len(live)} live'
    if done:
        out += f' · {done} done'
    if full and live:
        out += ' — ' + ', '.join(live)
    return out


def _render_cards(projects, facets, parsed, today, full):
    lines = []
    for p in sorted(projects, key=lambda q: str(q.path)):
        if lines:
            lines.append('')
        st = status_for(p, parsed.get('status', {}))
        qual = (f'{p.container}/{p.name}'
                if p.container and any(q.name == p.container for q in projects) else p.name)
        lines.append(f'{qual}   {_card_header(st, "projects" in facets, today)}'.rstrip())
        if 'claude.md' in facets:
            lines.append(_card_line('claude.md',
                                    _claude_md_detail(parsed.get('claude_md', {}).get(p.name))))
        if 'memory' in facets:
            lines.append(_card_line('memory', _memory_detail(st, today)))
        if 'sessions' in facets:
            lines.append(_card_line('sessions',
                                    _sessions_detail(parsed.get('sessions', {}).get(p.name, []),
                                                     today, full)))
        if 'plans' in facets:
            lines.append(_card_line('plans',
                                    _plans_detail(parsed.get('plans', {}).get(p.name, []))))
        if 'specs' in facets:
            lines.append(_card_line('specs',
                                    _specs_detail(parsed.get('specs', {}).get(p.name, []), full)))
    return lines


def build_atlas(projects, facets, parsed, depth, today, scope_label):
    """Final ATLAS text: '## Atlas …' header line + digest or cards body."""
    n = len(projects)
    header = f'## Atlas — {scope_label} · {n} project{"" if n == 1 else "s"} — {today.isoformat()}'
    if not projects:
        return f'{header}\n\n(no projects in scope)'
    body = (_render_cards(projects, facets, parsed, today, depth == 'full')
            if _mode(depth, n) == 'cards'
            else _render_digest(projects, facets, parsed, today))
    return '\n'.join([header, ''] + body)
