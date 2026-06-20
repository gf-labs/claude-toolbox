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
Output (dry-run): one JSON object per line, "PROPOSAL: {path, id8, current_title, name}", or "NONE"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope
from session_naming import derive_name, extract_context, read_title, write_title


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
            current_title = read_title(f)

            if current_title and not force:
                continue

            commit, first_user = extract_context(f)

            if pattern and pattern not in (current_title + ' ' + first_user).lower():
                continue

            if not commit and not first_user:
                continue

            name = derive_name(commit, first_user)
            if not name:
                continue

            results.append((f, f.stem[:8], current_title, name))

        except Exception as e:
            print(f'warning: could not process {f}: {e}', file=sys.stderr)

if not results:
    print('NONE')
    sys.exit(0)

for f, sid8, current_title, name in results:
    if dry_run:
        print('PROPOSAL: ' + json.dumps({
            'path': str(f), 'id8': sid8, 'current_title': current_title, 'name': name,
        }))
    else:
        write_title(f, name)
        print(f'RENAMED: {sid8} → {name}')
