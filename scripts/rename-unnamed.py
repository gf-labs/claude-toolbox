#!/usr/bin/env python3
"""Auto-rename unnamed sessions in scope from commit subjects or first user messages.

Usage:
  python3 rename-unnamed.py [--skip SESSION_ID_PREFIX]

--skip: skip the session with this ID prefix (default: skip most recent by mtime per project)

Outputs: "RENAMED: id8 → name" per session renamed, or "NONE" if nothing to rename.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope


def _extract_context(path: Path):
    """Return (last_commit_subject, first_user_msg) using head+tail reads."""
    text = path.read_text(errors='replace')
    lines = text.splitlines()

    # First user message — near the start
    first_user = ''
    for line in lines[:40]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'user':
                msg = obj.get('message', {})
                content = msg.get('content', '')
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

    # Last commit subject — scan end of file in reverse
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


def _slug(text: str) -> str:
    SKIP = {
        'session', 'work', 'update', 'changes', 'misc', 'the', 'a', 'an',
        'to', 'and', 'for', 'in', 'of', 'is', 'it', 'this', 'that', 'with',
        'some', 'my', 'your', 'we', 'i',
    }
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    words = [w for w in words if w not in SKIP and len(w) > 1][:5]
    return '-'.join(words)


def _derive_name(commit: str, first_user: str) -> str:
    if commit:
        # Strip "[main abc1234] " prefix
        m = re.match(r'^\[(?:main|master)[^\]]*\]\s*', commit)
        source = commit[m.end():] if m else commit
        # Strip conventional commit prefix: feat: fix(scope): chore!:
        source = re.sub(r'^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)[!]?(\([^)]+\))?:\s*', '', source)
        # Strip trailing version e.g. (v0.4.3)
        source = re.sub(r'\s*\(v[\d.]+\)\s*$', '', source).strip()
        name = _slug(source)
        if name:
            return name
    if first_user:
        # Strip leading /command invocations
        source = re.sub(r'^/\S+\s*', '', first_user).strip()
        return _slug(source)
    return ''


# --- Parse args ---
args = sys.argv[1:]
skip_prefix = None
if '--skip' in args:
    idx = args.index('--skip')
    if idx + 1 < len(args):
        skip_prefix = args[idx + 1]

# --- Resolve scope ---
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    proj_dirs = [projects_dir / data]
elif mode == 'parent':
    proj_dirs = [projects_dir / key for key, _ in data]
else:
    proj_dirs = sorted(d for d in projects_dir.iterdir() if d.is_dir())

renamed = []

for proj_dir in proj_dirs:
    if not proj_dir.exists():
        continue
    jsonls = sorted(proj_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
    if not jsonls:
        continue

    # Determine what to skip
    if skip_prefix:
        skip_stems = {f.stem for f in jsonls if f.stem.startswith(skip_prefix)}
    else:
        skip_stems = {jsonls[-1].stem}  # most recent = current session

    for f in jsonls:
        if f.stem in skip_stems:
            continue
        try:
            # Check existing title in a single pass, also grab context
            has_title = False
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('type') == 'custom-title' and obj.get('customTitle'):
                        has_title = True
                        break
                except Exception:
                    pass

            if has_title:
                continue

            commit, first_user = _extract_context(f)
            if not commit and not first_user:
                continue

            name = _derive_name(commit, first_user)
            if not name:
                continue

            sid = f.stem
            record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': sid})
            with open(f, 'a') as fh:
                fh.write(record + '\n')
            renamed.append(f'{sid[:8]} → {name}')

        except Exception:
            pass

if renamed:
    for r in renamed:
        print(f'RENAMED: {r}')
else:
    print('NONE')
