#!/usr/bin/env python3
"""Consolidated context collector for /tools:pin.

Replaces the ~13 separate collection blocks that pin.md used to run as individual
bash round-trips. Derives scope once, resolves the current-session JSONL once,
reads it in a single pass (files touched + bash commands + session title), and
emits every section pin.md needs as one structured blob.

Token discipline:
- session-log.md: emits only the LAST entry (+ a same-session match if separate),
  never the full file — pin only needs the last entry for the repeat-pin check.
- MEMORY.md: emits a tail + line count normally; full content only when a legacy
  snapshot migration is actually pending (MIGRATION_NEEDED).

Output is a flat, section-delimited text blob (=== SECTION ===) consumed by the
model. Sibling collectors with self-contained logic (plans, plugin drift) are
shelled out so they remain the single source of truth.
"""
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _scope import get_scope  # noqa: E402

HOME = Path.home()
PROJECTS_DIR = HOME / '.claude' / 'projects'
MEMORY_FULL_MAX_LINES = 250  # emit MEMORY.md whole below this; tail-only above it
MEMORY_TAIL_LINES = 60


def _run(cmd, cwd=None):
    """Run a command, return stripped stdout or None on any failure."""
    try:
        return subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL, text=True, cwd=cwd
        ).strip()
    except Exception:
        return None


# --- Resolve scope, project key, project dir -------------------------------
mode, data, cwd = get_scope()

git_root = _run(['git', 'rev-parse', '--show-toplevel'])

if mode == 'single':
    project_key = data
    project_dir = cwd
elif git_root:
    project_dir = Path(git_root)
    project_key = git_root.replace('/', '-')
else:
    print('=== SCOPE ===')
    print('MODE: global')
    print('ERROR: No project detected. Pin is project-scoped — run from within a repo.')
    sys.exit(0)

proj_meta_dir = PROJECTS_DIR / project_key
memory_dir = proj_meta_dir / 'memory'

repo = project_dir.name
# Domain = first path component under ~/Repos (matches pin.md slug derivation)
domain = ''
pd_str = str(project_dir)
if '/Repos/' in pd_str:
    domain = pd_str.split('/Repos/', 1)[1].split('/')[0]
tw_project = f'{domain}.{repo}' if domain else repo

print('=== SCOPE ===')
print(f'MODE: {mode}')
print(f'PROJECT_KEY: {project_key}')
print(f'PROJECT_DIR: {project_dir}')
print(f'REPO: {repo}')
print(f'TW_PROJECT: {tw_project}')
print(f'DATE: {date.today().isoformat()}')
print()


# --- Resolve current-session JSONL (sessions/ metadata, mtime fallback) -----
def _current_jsonl():
    jsonl_files = list(proj_meta_dir.glob('*.jsonl'))
    if not jsonl_files:
        return None
    best, best_started = None, -1
    sessions_dir = HOME / '.claude' / 'sessions'
    if sessions_dir.exists():
        for sf in sessions_dir.iterdir():
            try:
                obj = json.loads(sf.read_text(encoding='utf-8'))
            except Exception:
                continue
            if obj.get('cwd') == str(project_dir) and obj.get('sessionId'):
                cand = proj_meta_dir / (obj['sessionId'] + '.jsonl')
                started = obj.get('startedAt', 0)
                if cand.exists() and started > best_started:
                    best, best_started = cand, started
    if best is None:
        best = max(jsonl_files, key=lambda f: f.stat().st_mtime)
    return best


current = _current_jsonl()

# --- Single pass over the session JSONL: files, cross-project, bash, title ---
session_id = 'unknown'
title = ''
files_touched, cross_project, bash_commands = [], [], []

if current is not None:
    session_id = current.stem
    seen_files, seen_cross = set(), set()
    _claude = HOME / '.claude'
    _skip_prefixes = (
        _claude / 'file-history', _claude / 'debug',
        _claude / 'session-env', _claude / 'plugins',
    )
    for line in current.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        otype = obj.get('type')
        if otype == 'custom-title':
            title = obj.get('customTitle', '') or title
            continue
        if otype != 'assistant':
            continue
        content = obj.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get('type') != 'tool_use':
                continue
            name = item.get('name', '')
            inp = item.get('input', {})
            if name in ('Write', 'Edit'):
                fp = inp.get('file_path', '')
                if not fp:
                    continue
                fpp = Path(fp)
                is_session_jsonl = (
                    fpp.suffix == '.jsonl'
                    and fpp.is_relative_to(_claude / 'projects')
                )
                if is_session_jsonl or any(fpp.is_relative_to(p) for p in _skip_prefixes):
                    continue
                try:
                    rel = str(fpp.relative_to(project_dir))
                    if rel not in seen_files:
                        seen_files.add(rel)
                        files_touched.append(rel)
                except ValueError:
                    if fp not in seen_cross:
                        seen_cross.add(fp)
                        cross_project.append(fp)
            elif name == 'Bash' and len(bash_commands) < 3:
                cmd = inp.get('command', '').strip().splitlines()
                if cmd and cmd[0]:
                    bash_commands.append(cmd[0][:120])

print('=== SESSION ===')
print(f'SESSION: {session_id}')
print(f'TITLE: {title or "(untitled)"}')
if files_touched:
    print('FILES_TOUCHED:')
    for f in files_touched:
        print(f'  {f}')
else:
    print('FILES_TOUCHED: none')
if cross_project:
    print('CROSS_PROJECT_FILES:')
    for f in cross_project:
        print(f'  {f}')
else:
    print('CROSS_PROJECT_FILES: none')
if bash_commands:
    print(f'BASH_COMMANDS: {len(bash_commands)}')
    for c in bash_commands:
        print(f'  $ {c}')
else:
    print('BASH_COMMANDS: none')
print()


# --- Git ---------------------------------------------------------------------
print('=== GIT ===')
if git_root:
    status_sb = _run(['git', 'status', '-sb'], cwd=project_dir) or ''
    branch_line = status_sb.splitlines()[0] if status_sb else '## (unknown)'
    print(f'BRANCH: {branch_line.lstrip("# ").strip()}')
    changes = _run(['git', 'status', '--short'], cwd=project_dir)
    # Drop the branch header line that appears when status.branch=true is set.
    change_lines = [ln for ln in (changes or '').splitlines() if not ln.startswith('## ')]
    if change_lines:
        print('CHANGES:')
        for ln in change_lines:
            print(f'  {ln}')
    else:
        print('CHANGES: clean')
    log = _run(['git', 'log', '--oneline', '-10'], cwd=project_dir)
    print('GIT_LOG:')
    print('\n'.join(f'  {ln}' for ln in log.splitlines()) if log else '  none')
    diffstat = _run(['git', 'diff', 'HEAD', '--stat'], cwd=project_dir)
    print('GIT_DIFF_STAT:')
    print('\n'.join(f'  {ln}' for ln in diffstat.splitlines()) if diffstat else '  none')
else:
    print('BRANCH: not a git repo')
    print('CHANGES: —')
    print('GIT_LOG: none')
    print('GIT_DIFF_STAT: none')
print()


# --- Backlog (TaskWarrior) ---------------------------------------------------
print('=== BACKLOG ===')
if _run(['task', '--version']):
    in_prog = _run(['task', 'rc.verbose=nothing', f'project:{tw_project}', '+ACTIVE', 'list'])
    up_next = _run(['task', 'rc.verbose=nothing', f'project:{tw_project}', 'limit:3', 'list'])
    print('IN_PROGRESS:')
    print('\n'.join(f'  {ln}' for ln in in_prog.splitlines()) if in_prog else '  (none)')
    print('UP_NEXT:')
    print('\n'.join(f'  {ln}' for ln in up_next.splitlines()) if up_next else '  (none)')
else:
    print('IN_PROGRESS: (task not installed)')
    print('UP_NEXT: (task not installed)')
print()


# --- Status: snapshot + session-log metadata ---------------------------------
mem_file = memory_dir / 'MEMORY.md'
log_file = memory_dir / 'session-log.md'

mem_text = mem_file.read_text(encoding='utf-8') if mem_file.exists() else ''
log_text = log_file.read_text(encoding='utf-8') if log_file.exists() else ''

# Snapshot info from MEMORY.md
snap_dates = re.findall(r'## Session snapshot — (\d{4}-\d{2}-\d{2})', mem_text)
last_snapshot = snap_dates[-1] if snap_dates else '—'
sessions_since = '—'
if last_snapshot != '—':
    try:
        cutoff = datetime.strptime(last_snapshot, '%Y-%m-%d').timestamp() + 86400
        newer = sum(1 for f in proj_meta_dir.glob('*.jsonl') if f.stat().st_mtime > cutoff)
        sessions_since = str(newer) if newer else '—'
    except Exception:
        pass

# Session-log metadata
log_dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', log_text, re.MULTILINE)
last_log = log_dates[-1] if log_dates else '—'
log_entries = str(len(log_dates)) if log_dates else '—'

print('=== STATUS ===')
print(f'LAST_SNAPSHOT: {last_snapshot}')
print(f'SESSIONS_SINCE: {sessions_since}')
print(f'LAST_SESSION_LOG: {last_log}')
print(f'LOG_ENTRIES: {log_entries}')
print()


# --- Session log: last entry + repeat-pin detection (NOT full file) ----------
print('=== SESSION_LOG ===')
print(f'PATH: {log_file}')
if not log_text:
    print('STATE: MISSING — will be created on first save')
    print('REPEAT_PIN: no')
else:
    # Split into entries by top-level "## " headers
    parts = re.split(r'(?m)^(?=## )', log_text)
    entries = [p for p in parts if p.strip().startswith('## ')]
    sid8 = session_id[:8] if session_id != 'unknown' else None
    matching = [e for e in entries if sid8 and sid8 in e.splitlines()[0]] if sid8 else []
    if matching:
        n = len(matching)
        print(f'REPEAT_PIN: yes — {n} prior entr{"y" if n == 1 else "ies"} this session; '
              f'next header suffix: ({n + 1})')
    else:
        print('REPEAT_PIN: no')
    last_entry = entries[-1].rstrip() if entries else ''
    print('LAST_ENTRY (append anchor — match its tail when appending):')
    print(last_entry)
    # On a repeat pin, surface EVERY same-session entry so the new draft can
    # dedup against all prior pins this session, not just the most recent.
    if matching:
        print('SAME_SESSION_ENTRIES (dedup the new draft against all of these):')
        for e in matching:
            print(e.rstrip())
            print()
print()


# --- Memory: migration flag + tail (full content only if migrating) ----------
print('=== MEMORY ===')
print(f'PATH: {mem_file}')
if not mem_text:
    print('STATE: MISSING — will be created')
    print('MIGRATION: none')
    print('LINES: 0')
else:
    n_snap = len(snap_dates)
    mem_lines = mem_text.splitlines()
    print(f'LINES: {len(mem_lines)}')
    print(f'MIGRATION: {n_snap} snapshot section(s) found' if n_snap else 'MIGRATION: none')
    if n_snap:
        print('MIGRATION_NEEDED: yes')
    # Step 3 appends to MEMORY.md and needs full content to dedup against and (when
    # migrating) to rewrite. MEMORY is bounded by design (wrap warns at 150 lines),
    # so emit it whole — only fall back to a tail for pathologically large files.
    if len(mem_lines) <= MEMORY_FULL_MAX_LINES:
        print('CONTENT:')
        print(mem_text.rstrip())
    else:
        print(f'⚠ LARGE ({len(mem_lines)} lines) — consider archiving older sections')
        print(f'TAIL (last {MEMORY_TAIL_LINES} lines, for dedup awareness):')
        print('\n'.join(mem_lines[-MEMORY_TAIL_LINES:]))
print()


# --- Plans (delegate to single source of truth) ------------------------------
print('=== PLANS ===')
plans = _run(['python3', str(SCRIPT_DIR / 'collect-plans.py')])
print(plans if plans else 'NONE')
print()


# --- Plugin drift (delegate) -------------------------------------------------
print('=== PLUGIN_DRIFT ===')
drift = _run(['python3', str(SCRIPT_DIR / 'collect-plugin-drift.py')])
print(drift if drift else 'unavailable')
print()


# --- Ramp: nodes due today ---------------------------------------------------
print('=== RAMP ===')
graph = HOME / '.claude' / 'knowledge-graphs' / 'claude-code.md'
if not graph.exists():
    print('RAMP: no graph')
else:
    try:
        gtext = graph.read_text(encoding='utf-8')
        today = date.today().isoformat()
        due = [m for m in re.findall(r'next: (\d{4}-\d{2}-\d{2})', gtext) if m <= today]
        lvl = re.search(r'^level: (.+)$', gtext, re.MULTILINE)
        xp = re.search(r'^xp: (\d+)$', gtext, re.MULTILINE)
        print(f'RAMP: {len(due)} nodes due  |  {lvl.group(1) if lvl else "?"}  |  '
              f'{xp.group(1) if xp else "?"} XP')
    except Exception:
        print('RAMP: no graph')
