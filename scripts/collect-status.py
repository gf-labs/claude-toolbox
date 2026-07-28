#!/usr/bin/env python3
"""Multi-repo git status collection — outputs tab-separated rows for parent/global mode."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _projects import enumerate_projects, global_scope, group, stale_keys
from _scope import get_scope, project_key


def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _log_info(proj_dir):
    """Return (last_log_date, entry_count) from session-log.md."""
    log_file = proj_dir / 'memory' / 'session-log.md'
    if not log_file.exists():
        return '—', '—'
    text = log_file.read_text(encoding='utf-8')
    dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if not dates:
        return '—', '—'
    return dates[-1], str(len(dates))


def _snapshot_info(mem_file):
    """Return (last_snapshot_date, sessions_since) from MEMORY.md."""
    if not mem_file.exists():
        return '—', '—'
    text = mem_file.read_text(encoding='utf-8')
    dates = re.findall(r'## Session snapshot — (\d{4}-\d{2}-\d{2})', text)
    last_date = dates[-1] if dates else '—'
    if last_date == '—':
        return '—', '—'
    proj_dir = mem_file.parent.parent  # ~/.claude/projects/[key]
    try:
        import datetime
        cutoff = datetime.datetime.strptime(last_date, '%Y-%m-%d').timestamp()
        cutoff += 86400
        newer = sum(1 for f in proj_dir.glob('*.jsonl') if f.stat().st_mtime > cutoff)
        return last_date, str(newer) if newer else '—'
    except (OSError, ValueError):
        return last_date, '—'


def _session_count(proj_dir):
    """Count .jsonl session files in a project directory."""
    if not proj_dir.exists():
        return '0'
    count = sum(1 for _ in proj_dir.glob('*.jsonl'))
    return str(count)


def _local_branch_count(path):
    """Count local git branches."""
    out = _run(['git', '-C', str(path), 'branch'])
    if not out:
        return '—'
    return str(len([ln for ln in out.splitlines() if ln.strip()]))


def _emit_row(name, path, group, projects_dir):
    """Print one tab-separated project row."""
    is_header = (group == 'header')
    if is_header:
        branch = '—'
        branches = '—'
        changes_str = '—'
        last_hash = '—'
        last_date = '—'
    else:
        branch = _run(['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD']) or '?'
        branches = _local_branch_count(path)
        status_out = _run(['git', '-C', str(path), 'status', '--short']) or ''
        changes = len([ln for ln in status_out.splitlines() if ln.strip()])
        changes_str = str(changes) if changes else '—'
        last_commit = _run(['git', '-C', str(path), 'log', '-1', '--format=%h\t%cs'])
        if last_commit and '\t' in last_commit:
            last_hash, last_date = last_commit.split('\t', 1)
        else:
            last_hash, last_date = '?', '—'

    proj_key = project_key(path, projects_dir)
    proj_dir = projects_dir / proj_key
    sessions = _session_count(proj_dir)
    mem_file = proj_dir / 'memory' / 'MEMORY.md'
    if mem_file.exists():
        mem_lines = len(mem_file.read_text(encoding='utf-8').splitlines())
        mem_status = 'WARN' if mem_lines >= 150 else ('OK' if mem_lines >= 50 else 'THIN')
        mem_str = f'{mem_lines}L'
    else:
        mem_status = 'MISSING'
        mem_str = 'none'

    backlog_file = path / 'BACKLOG.md'
    backlog_count = '—'
    if backlog_file.exists():
        try:
            bl_lines = backlog_file.read_text(encoding='utf-8').splitlines()[:50]
            items = [ln for ln in bl_lines if ln.strip() and not ln.startswith('#')]
            backlog_count = str(len(items)) if items else '—'
        except (OSError, ValueError):
            pass

    last_snap, sessions_since = _snapshot_info(mem_file)
    last_log, log_entries = _log_info(proj_dir)

    print(f'{group}\t{name}\t{branch}\t{branches}\t{sessions}\t{changes_str}\t{last_hash}\t{mem_str}\t{mem_status}\t{backlog_count}\t{last_snap}\t{sessions_since}\t{last_log}\t{log_entries}\t{last_date}')


mode, data, cwd = get_scope()
if '--all' in sys.argv[1:]:
    mode, data, cwd = global_scope()  # force the cross-project walk regardless of cwd
projects_dir = Path.home() / '.claude' / 'projects'

# --- Single mode ---
if mode == 'single':
    proj_key = data
    mem_file = projects_dir / proj_key / 'memory' / 'MEMORY.md'
    last_snap, sessions_since = _snapshot_info(mem_file)
    print(f'SINGLE {cwd}')
    print(f'LAST_SNAPSHOT\t{last_snap}\tSESSIONS_SINCE\t{sessions_since}')
    sys.exit(0)

# --- Active projects (typed; deterministic nearest-ancestor containers via _projects) ---
projects = enumerate_projects(scope=(mode, data, cwd))
grouped = group(projects)  # container name -> [Project]; None key = top-level

# --- Output ---
print('GROUP\tPROJECT\tBRANCH\tLOCAL_BRANCHES\tSESSIONS\tCHANGES\tLAST_COMMIT\tMEMORY_LINES\tMEMORY_STATUS\tBACKLOG_ITEMS\tLAST_SNAPSHOT\tSESSIONS_SINCE\tLAST_SESSION_LOG\tLOG_ENTRIES\tLAST_COMMIT_DATE')

_emitted = set()


def _emit_tree(pr):
    """Emit pr, then its children depth-first. Guard-first: the _emitted set makes
    name-collision cycles impossible, and the trailing sweep below guarantees every
    project renders exactly once (the old one-level render silently dropped rows)."""
    if str(pr.path) in _emitted:
        return
    _emitted.add(str(pr.path))
    kids = sorted(grouped.get(pr.name, []), key=lambda q: str(q.path))
    _emit_row(pr.name, pr.path, 'header' if kids else (pr.container or ''), projects_dir)
    for child in kids:
        _emit_tree(child)


for _pr in sorted(grouped.get(None, []), key=lambda q: str(q.path)):
    _emit_tree(_pr)
# Never drop a row: sweep anything not reachable from a top-level root
# (possible under duplicate project names, where group()'s name keys collide).
for _pr in sorted(projects, key=lambda q: str(q.path)):
    _emit_tree(_pr)

# --- Stale detection (always global — not scoped) ---
orphaned_entries, unscoped_entries = stale_keys(projects_dir=projects_dir,
                                                active_keys={p.key for p in projects})

if orphaned_entries:
    print('')
    print('# ORPHANED_KEYS')
    print('KEY\tSESSIONS\tNOTE')
    for key, note in orphaned_entries:
        proj_dir = projects_dir / key
        sessions = _session_count(proj_dir)
        print(f'{key}\t{sessions}\t{note}')

if unscoped_entries:
    print('')
    print('# UNSCOPED_KEYS')
    print('KEY\tSESSIONS\tNOTE')
    for key, note in unscoped_entries:
        proj_dir = projects_dir / key
        sessions = _session_count(proj_dir)
        print(f'{key}\t{sessions}\t{note}')
