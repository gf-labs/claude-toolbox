#!/usr/bin/env python3
"""Post-session-save: name current session and rename unnamed sessions in scope.

Called after saving the session log in /tools:pin and /tools:wrap.
No arguments needed — derives name from git commit or first user message,
determines current session by mtime, and handles --skip internally.

Output:
  "Named: <name>"         if current session was unnamed and got a name
  "Renamed: a→x, b→y"    if other unnamed sessions were renamed (omitted if none)
  "NONE"                  if nothing was done
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_index import get_status as _get_registry_status


def _extract_context(path: Path) -> tuple[str, str]:
    """Return (last_commit_subject, first_user_msg) from a JSONL session file."""
    lines = path.read_text(errors='replace').splitlines()

    first_user = ''
    for line in lines[:40]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'user':
                content = obj.get('message', {}).get('content', '')
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'text':
                            first_user = c.get('text', '')[:150]
                            break
                elif isinstance(content, str):
                    first_user = content[:150]
                if first_user:
                    break
        except Exception:
            pass

    commit = ''
    for line in reversed(lines[-600:]):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'assistant':
                for block in obj.get('message', {}).get('content', []):
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'tool_result':
                        for inner in block.get('content', []):
                            if isinstance(inner, dict) and inner.get('type') == 'text':
                                for ln in inner.get('text', '').splitlines():
                                    if ln.startswith('[main') or ln.startswith('[master'):
                                        commit = ln
                                        break
        except Exception:
            pass
        if commit:
            break

    return commit, first_user


_SKIP_WORDS = {
    'session', 'work', 'update', 'changes', 'misc', 'the', 'a', 'an',
    'to', 'and', 'for', 'in', 'of', 'is', 'it', 'this', 'that', 'with',
    'some', 'my', 'your', 'we', 'i',
}


def _slug(text: str) -> str:
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    words = [w for w in words if w not in _SKIP_WORDS and len(w) > 1][:5]
    return '-'.join(words)


def _derive_name(commit: str, first_user: str) -> str:
    if commit:
        m = re.match(r'^\[(?:main|master)[^\]]*\]\s*', commit)
        source = commit[m.end():] if m else commit
        source = re.sub(
            r'^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)[!]?(\([^)]+\))?:\s*',
            '', source,
        )
        source = re.sub(r'\s*\(v[\d.]+\)\s*$', '', source).strip()
        name = _slug(source)
        if name:
            return name
    if first_user:
        source = re.sub(r'^/\S+\s*', '', first_user).strip()
        return _slug(source)
    return ''


def _get_title(path: Path) -> str:
    title = ''
    for line in path.read_text(errors='replace').splitlines():
        try:
            obj = json.loads(line)
            if obj.get('type') == 'custom-title':
                title = obj.get('customTitle', '')
        except Exception:
            pass
    return title


def _write_title(path: Path, name: str) -> None:
    record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': path.stem})
    with open(path, 'a') as fh:
        fh.write(record + '\n')


mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    proj_dirs = [projects_dir / data]
elif mode == 'parent':
    proj_dirs = [projects_dir / key for key, _ in data]
else:
    proj_dirs = sorted(d for d in projects_dir.iterdir() if d.is_dir())

named_current = ''
renamed = []

for proj_dir in proj_dirs:
    if not proj_dir.exists():
        continue
    jsonls = sorted(proj_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
    if not jsonls:
        continue

    current = jsonls[-1]  # most recent by mtime = active session

    # Name current session if unnamed and not registry-protected
    if not _get_title(current):
        if _get_registry_status(proj_dir.name, current.stem) not in ('done', 'keep'):
            commit, first_user = _extract_context(current)
            name = _derive_name(commit, first_user)
            if name:
                _write_title(current, name)
                named_current = name

    # Rename other unnamed sessions in this project
    for f in jsonls[:-1]:
        if _get_title(f):
            continue
        if _get_registry_status(proj_dir.name, f.stem) in ('done', 'keep'):
            continue
        commit, first_user = _extract_context(f)
        if not commit and not first_user:
            continue
        name = _derive_name(commit, first_user)
        if not name:
            continue
        _write_title(f, name)
        renamed.append(f'{f.stem[:8]}→{name}')

did_something = False
if named_current:
    print(f'Named: {named_current}')
    did_something = True
if renamed:
    print(f'Renamed: {", ".join(renamed)}')
    did_something = True
if not did_something:
    print('NONE')
