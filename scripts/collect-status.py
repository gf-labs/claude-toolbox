#!/usr/bin/env python3
"""Multi-repo git status collection — outputs tab-separated rows for parent/global mode."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import _reconstruct, get_scope


def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
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
    except Exception:
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
    else:
        branch = _run(['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD']) or '?'
        branches = _local_branch_count(path)
        status_out = _run(['git', '-C', str(path), 'status', '--short']) or ''
        changes = len([ln for ln in status_out.splitlines() if ln.strip()])
        changes_str = str(changes) if changes else '—'
        last_commit = _run(['git', '-C', str(path), 'log', '--oneline', '-1']) or '?'
        last_hash = last_commit.split()[0] if last_commit.split() else '?'

    proj_key = str(path).replace('/', '-')
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
        except Exception:
            pass

    last_snap, sessions_since = _snapshot_info(mem_file)
    last_log, log_entries = _log_info(proj_dir)

    print(f'{group}\t{name}\t{branch}\t{branches}\t{sessions}\t{changes_str}\t{last_hash}\t{mem_str}\t{mem_status}\t{backlog_count}\t{last_snap}\t{sessions_since}\t{last_log}\t{log_entries}')


mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

# --- Single mode ---
if mode == 'single':
    proj_key = str(cwd).replace('/', '-')
    mem_file = projects_dir / proj_key / 'memory' / 'MEMORY.md'
    last_snap, sessions_since = _snapshot_info(mem_file)
    print(f'SINGLE {cwd}')
    print(f'LAST_SNAPSHOT\t{last_snap}\tSESSIONS_SINCE\t{sessions_since}')
    sys.exit(0)

# --- Build active project list ---
if mode == 'parent':
    active = list(data)  # [(key, path), ...]
else:
    seen = set()
    active = []
    for proj_key_dir in sorted(projects_dir.iterdir()):
        if not proj_key_dir.is_dir():
            continue
        for path in _reconstruct(proj_key_dir.name, None):
            if path not in seen and path != Path.home():
                seen.add(path)
                active.append((proj_key_dir.name, path))

# --- Group detection: find parent→children relationships within active list ---
all_paths = {str(p) for _, p in active}
groups = {}  # str(parent_path) → [(key, path)]
top_level = []
for key, path in active:
    parent_str = next(
        (ps for ps in all_paths if str(path).startswith(ps + '/') and ps != str(path)),
        None
    )
    if parent_str:
        groups.setdefault(parent_str, []).append((key, path))
    else:
        top_level.append((key, path))

# --- Stale detection (always global — not scoped) ---
active_keys = {key for key, _ in active}
all_proj_keys = [p.name for p in sorted(projects_dir.iterdir()) if p.is_dir()]
with_dash = {k for k in all_proj_keys if k.startswith('-')}
orphaned_entries = []   # no dir on disk, or duplicate key
unscoped_entries = []   # dir exists but it's the home dir
for key in all_proj_keys:
    if key in active_keys:
        continue
    if not key.startswith('-') and ('-' + key) in with_dash:
        orphaned_entries.append((key, 'duplicate (no leading dash)'))
        continue
    candidates = list(_reconstruct(key, None))
    if not candidates:
        orphaned_entries.append((key, 'no dir on disk'))
        continue
    if candidates[0] == Path.home():
        unscoped_entries.append((key, 'home dir — unscoped sessions'))

# --- Output ---
print('GROUP\tPROJECT\tBRANCH\tLOCAL_BRANCHES\tSESSIONS\tCHANGES\tLAST_COMMIT\tMEMORY_LINES\tMEMORY_STATUS\tBACKLOG_ITEMS\tLAST_SNAPSHOT\tSESSIONS_SINCE\tLAST_SESSION_LOG\tLOG_ENTRIES')

for _key, path in top_level:
    has_children = str(path) in groups
    group_tag = 'header' if has_children else ''
    _emit_row(path.name, path, group_tag, projects_dir)
    for _child_key, child_path in groups.get(str(path), []):
        _emit_row(child_path.name, child_path, path.name, projects_dir)

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
