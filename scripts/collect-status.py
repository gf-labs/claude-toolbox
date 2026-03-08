#!/usr/bin/env python3
"""Multi-repo git status collection — outputs tab-separated rows for parent/global mode."""
import re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope


def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def _snapshot_info(mem_file):
    """Return (last_snapshot_date, sessions_since) from MEMORY.md."""
    if not mem_file.exists():
        return '—', '—'
    text = mem_file.read_text()
    # Find all snapshot headers: ## Session snapshot — YYYY-MM-DD
    dates = re.findall(r'## Session snapshot — (\d{4}-\d{2}-\d{2})', text)
    last_date = dates[-1] if dates else '—'

    # Count sessions in the project dir newer than last snapshot
    if last_date == '—':
        return '—', '—'
    proj_dir = mem_file.parent.parent  # ~/.claude/projects/[key]
    try:
        import datetime
        cutoff = datetime.datetime.strptime(last_date, '%Y-%m-%d').timestamp()
        # Add one full day so same-day sessions count as snapshotted
        cutoff += 86400
        newer = sum(
            1 for f in proj_dir.glob('*.jsonl')
            if f.stat().st_mtime > cutoff
        )
        return last_date, str(newer) if newer else '—'
    except Exception:
        return last_date, '—'


mode, data, cwd = get_scope()

projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    cwd_key = str(cwd).replace('/', '-')
    mem_file = projects_dir / cwd_key / 'memory' / 'MEMORY.md'
    last_snap, sessions_since = _snapshot_info(mem_file)
    print(f'SINGLE {cwd}')
    print(f'LAST_SNAPSHOT\t{last_snap}\tSESSIONS_SINCE\t{sessions_since}')
    sys.exit(0)

if mode == 'parent':
    projects = [(c.name, c) for _, c in data]
else:
    # Global: iterate all known claude projects and reconstruct paths.
    # Key format: str(path).replace('/', '-') → '-Users-berniegreen-...'
    # Reverse is ambiguous for dirs with hyphens, so only include paths that exist.
    projects = []
    for proj_key in sorted(projects_dir.iterdir()):
        if not proj_key.is_dir():
            continue
        reconstructed = Path('/' + proj_key.name[1:].replace('-', '/'))
        if reconstructed.is_dir():
            projects.append((reconstructed.name, reconstructed))

print('PROJECT\tBRANCH\tCHANGES\tLAST_COMMIT\tMEMORY_LINES\tMEMORY_STATUS\tBACKLOG_ITEMS\tLAST_SNAPSHOT\tSESSIONS_SINCE')

for name, path in projects:
    branch = _run(['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD']) or '?'

    status_out = _run(['git', '-C', str(path), 'status', '--short']) or ''
    changes = len([l for l in status_out.splitlines() if l.strip()])
    changes_str = str(changes) if changes else '—'

    last_commit = _run(['git', '-C', str(path), 'log', '--oneline', '-1']) or '?'
    last_hash = last_commit.split()[0] if last_commit.split() else '?'

    cwd_key = str(path).replace('/', '-')
    mem_file = projects_dir / cwd_key / 'memory' / 'MEMORY.md'
    if mem_file.exists():
        lines = len(mem_file.read_text().splitlines())
        if lines >= 150:
            mem_status = 'WARN'
        elif lines >= 50:
            mem_status = 'OK'
        else:
            mem_status = 'THIN'
        mem_str = f'{lines}L'
    else:
        mem_status = 'MISSING'
        mem_str = 'none'

    backlog_file = path / 'BACKLOG.md'
    backlog_count = '—'
    if backlog_file.exists():
        try:
            bl_lines = backlog_file.read_text().splitlines()[:50]
            items = [l for l in bl_lines if l.strip() and not l.startswith('#')]
            backlog_count = str(len(items)) if items else '—'
        except Exception:
            pass

    last_snap, sessions_since = _snapshot_info(mem_file)

    print(f'{name}\t{branch}\t{changes_str}\t{last_hash}\t{mem_str}\t{mem_status}\t{backlog_count}\t{last_snap}\t{sessions_since}')
