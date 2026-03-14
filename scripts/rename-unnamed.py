#!/usr/bin/env python3
"""Rename unnamed sessions in scope from commit subjects or first user messages.

Usage:
  python3 rename-unnamed.py [options]

Options:
  --skip ID       skip session with this ID prefix (default: most recent per project)
  --pattern TEXT  only process sessions whose title or first message matches TEXT
  --force         include sessions that already have a custom-title
  --dry-run       print proposals without writing; outputs PROPOSAL lines instead of RENAMED

Output (normal):  "RENAMED: id8 → name"  or  "NONE"
Output (dry-run): "PROPOSAL: /path/to/file|id8|current_title|proposed_name"  or  "NONE"
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope


def _extract_context(path: Path):
    """Return (last_commit_subject, first_user_msg) using head+tail reads."""
    lines = path.read_text(errors='replace').splitlines()

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
        m = re.match(r'^\[(?:main|master)[^\]]*\]\s*', commit)
        source = commit[m.end():] if m else commit
        source = re.sub(r'^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)[!]?(\([^)]+\))?:\s*', '', source)
        source = re.sub(r'\s*\(v[\d.]+\)\s*$', '', source).strip()
        name = _slug(source)
        if name:
            return name
    if first_user:
        source = re.sub(r'^/\S+\s*', '', first_user).strip()
        return _slug(source)
    return ''


# --- Parse args ---
args = sys.argv[1:]

def _flag(name):
    return name in args

def _opt(name):
    if name in args:
        idx = args.index(name)
        return args[idx + 1] if idx + 1 < len(args) else None
    return None

skip_prefix = _opt('--skip')
pattern = (_opt('--pattern') or '').lower()
force = _flag('--force')
dry_run = _flag('--dry-run')

# --- Resolve scope ---
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    proj_dirs = [projects_dir / data]
elif mode == 'parent':
    proj_dirs = [projects_dir / key for key, _ in data]
else:
    proj_dirs = sorted(d for d in projects_dir.iterdir() if d.is_dir())

results = []

for proj_dir in proj_dirs:
    if not proj_dir.exists():
        continue
    jsonls = sorted(proj_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
    if not jsonls:
        continue

    if skip_prefix:
        skip_stems = {f.stem for f in jsonls if f.stem.startswith(skip_prefix)}
    else:
        skip_stems = {jsonls[-1].stem}

    for f in jsonls:
        if f.stem in skip_stems:
            continue
        try:
            current_title = ''
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('type') == 'custom-title' and obj.get('customTitle'):
                        current_title = obj['customTitle']
                except Exception:
                    pass

            if current_title and not force:
                continue

            commit, first_user = _extract_context(f)

            if pattern and pattern not in (current_title + ' ' + first_user).lower():
                continue

            if not commit and not first_user:
                continue

            name = _derive_name(commit, first_user)
            if not name:
                continue

            results.append((f, f.stem[:8], current_title, name))

        except Exception:
            pass

if not results:
    print('NONE')
    sys.exit(0)

for f, sid8, current_title, name in results:
    if dry_run:
        print(f'PROPOSAL: {f}|{sid8}|{current_title}|{name}')
    else:
        record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': f.stem})
        with open(f, 'a') as fh:
            fh.write(record + '\n')
        print(f'RENAMED: {sid8} → {name}')
