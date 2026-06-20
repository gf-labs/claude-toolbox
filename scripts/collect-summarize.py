#!/usr/bin/env python3
"""Parse current session JSONL to extract files touched and bash commands."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

mode, data, cwd = get_scope()

if mode == 'single':
    cwd_key = data
elif cwd is not None:
    cwd_key = str(cwd).replace('/', '-')
else:
    try:
        import subprocess
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        cwd = Path(git_root)
        cwd_key = str(cwd).replace('/', '-')
    except (OSError, subprocess.SubprocessError):
        print('ERROR: Could not determine project directory')
        sys.exit(1)

if cwd is None:
    cwd = Path('/' + cwd_key[1:].replace('-', '/'))

projects_dir = Path.home() / '.claude' / 'projects'
proj_dir = projects_dir / cwd_key

jsonl_files = list(proj_dir.glob('*.jsonl'))
if not jsonl_files:
    print('SESSION: unknown')
    print(f'PROJECT_KEY: {cwd_key}')
    print(f'PROJECT_DIR: {cwd}')
    print()
    print('FILES_TOUCHED: none')
    print()
    print('CROSS_PROJECT_FILES: none')
    print()
    print('BASH_COMMANDS: none')
    sys.exit(0)

# Prefer sessions/ directory for accurate current-session detection.
# mtime-based selection fails when an unrelated JSONL is modified (e.g. title edits).
current = None
_best_started = -1
sessions_dir = Path.home() / '.claude' / 'sessions'
if sessions_dir.exists():
    for sf in sessions_dir.iterdir():
        try:
            obj = json.loads(sf.read_text(encoding='utf-8'))
            if obj.get('cwd') == str(cwd) and obj.get('sessionId'):
                candidate = proj_dir / (obj['sessionId'] + '.jsonl')
                started = obj.get('startedAt', 0)
                if candidate.exists() and started > _best_started:
                    current = candidate
                    _best_started = started
        except Exception:
            pass

if current is None:
    # Fallback: most recently modified JSONL (may be inaccurate if old files were touched)
    current = max(jsonl_files, key=lambda f: f.stat().st_mtime)

session_id = current.stem

files_touched = []   # relative to project root, deduped, ordered by first appearance
cross_project = []   # absolute paths outside project root, deduped
bash_commands = []

seen_files = set()
seen_cross = set()

for line in current.read_text(encoding='utf-8', errors='replace').splitlines():
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        continue

    if obj.get('type') != 'assistant':
        continue

    msg = obj.get('message', {})
    content = msg.get('content', [])
    if not isinstance(content, list):
        continue

    for item in content:
        if not isinstance(item, dict) or item.get('type') != 'tool_use':
            continue
        name = item.get('name', '')
        inp = item.get('input', {})

        if name in ('Write', 'Edit'):
            fp = inp.get('file_path', '')
            if fp:
                fp_path = Path(fp)
                # Skip Claude internal dirs — but allow ~/.claude/projects/*/memory/* writes
                # (MEMORY.md, session-log.md) so they appear in CROSS_PROJECT_FILES correctly.
                _claude = Path.home() / '.claude'
                _skip_prefixes = (
                    _claude / 'file-history',
                    _claude / 'debug',
                    _claude / 'session-env',
                    _claude / 'plugins',
                )
                _is_session_jsonl = (
                    fp_path.suffix == '.jsonl'
                    and fp_path.is_relative_to(_claude / 'projects')
                )
                _is_internal = _is_session_jsonl or any(
                    fp_path.is_relative_to(p) for p in _skip_prefixes
                )
                if _is_internal:
                    continue
                try:
                    rel = str(fp_path.relative_to(cwd))
                    if rel not in seen_files:
                        seen_files.add(rel)
                        files_touched.append(rel)
                except ValueError:
                    if fp not in seen_cross:
                        seen_cross.add(fp)
                        cross_project.append(fp)

        elif name == 'Bash' and len(bash_commands) < 3:
            cmd = inp.get('command', '').strip().splitlines()[0][:120]
            if cmd:
                bash_commands.append(cmd)

print(f'SESSION: {session_id}')
print(f'PROJECT_KEY: {cwd_key}')
print(f'PROJECT_DIR: {cwd}')
print()

if files_touched:
    print('FILES_TOUCHED:')
    for f in files_touched:
        print(f'  {f}')
else:
    print('FILES_TOUCHED: none')

print()

if cross_project:
    print('CROSS_PROJECT_FILES:')
    for f in cross_project:
        print(f'  {f}')
else:
    print('CROSS_PROJECT_FILES: none')

print()

if bash_commands:
    print(f'BASH_COMMANDS: {len(bash_commands)}')
    for cmd in bash_commands:
        print(f'  $ {cmd}')
else:
    print('BASH_COMMANDS: none')
