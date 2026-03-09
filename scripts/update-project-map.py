#!/usr/bin/env python3
"""Update ~/.claude/plans/.project-map with current session's cross-project references.

Called by tools:wrap after each session. Reads collect-summarize.py output from stdin,
or runs it automatically if stdin is a tty.

The project map tracks:
  - first_session: oldest JSONL for each project key (when it first appeared in Claude)
  - Referenced by: sessions from other projects that touched this project's files
"""
import json, re, subprocess, sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import _reconstruct

MAP_FILE = Path.home() / '.claude' / 'plans' / '.project-map'
PROJECTS_DIR = Path.home() / '.claude' / 'projects'


def get_first_session(key: str) -> str:
    proj_dir = PROJECTS_DIR / key
    if not proj_dir.exists():
        return 'unknown'
    jsonls = list(proj_dir.glob('*.jsonl'))
    if not jsonls:
        return 'unknown'
    oldest = min(jsonls, key=lambda f: f.stat().st_mtime)
    d = datetime.fromtimestamp(oldest.stat().st_mtime).date().isoformat()
    return f'{d} · {oldest.stem[:8]}'


def find_project_for_path(abs_path_str: str) -> tuple[str, str] | None:
    """Walk parent dirs to find which project key owns this path."""
    p = Path(abs_path_str)
    for parent in list(p.parents):
        key = str(parent).replace('/', '-')
        if (PROJECTS_DIR / key).exists():
            return key, parent.name
    return None, None


def parse_map() -> dict:
    """Parse .project-map → {key: {name, first_session, refs: [str]}}"""
    if not MAP_FILE.exists():
        return {}
    text = MAP_FILE.read_text()
    projects = {}
    current = None
    in_refs = False
    for line in text.splitlines():
        if line.startswith('## ') and ' · ' in line:
            parts = line[3:].split(' · ', 1)
            current = parts[1].strip()
            projects[current] = {'name': parts[0].strip(), 'first_session': '', 'refs': []}
            in_refs = False
        elif current is None:
            continue
        elif line.startswith('- First session: '):
            projects[current]['first_session'] = line[17:].strip()
        elif line.startswith('- Referenced by:'):
            in_refs = True
        elif line.strip() == '- Referenced by: none':
            in_refs = False
        elif in_refs and line.startswith('  - '):
            projects[current]['refs'].append(line[4:].strip())
        elif not line.strip():
            in_refs = False
    return projects


def write_map(projects: dict):
    today = date.today().isoformat()
    lines = ['# .project-map', f'# Updated: {today}', '']
    for key in sorted(projects, key=lambda k: projects[k]['name'].lower()):
        info = projects[key]
        lines.append(f"## {info['name']} · {key}")
        lines.append(f"- First session: {info['first_session']}")
        refs = info.get('refs', [])
        if refs:
            lines.append('- Referenced by:')
            for r in refs:
                lines.append(f'  - {r}')
        else:
            lines.append('- Referenced by: none')
        lines.append('')
    MAP_FILE.write_text('\n'.join(lines))


# --- Run collect-summarize if needed ---
if sys.stdin.isatty():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / 'collect-summarize.py')],
        capture_output=True, text=True
    )
    lines = result.stdout.splitlines()
else:
    lines = sys.stdin.read().splitlines()

# Parse output
session_id = None
source_key = None
cross_files = []
in_cross = False

for line in lines:
    if line.startswith('SESSION: '):
        session_id = line[9:].strip()
    elif line.startswith('PROJECT_KEY: '):
        source_key = line[13:].strip()
    elif line.startswith('CROSS_PROJECT_FILES:'):
        in_cross = True
        val = line[20:].strip()
        if val and val not in ('none', ''):
            cross_files.append(val)
    elif in_cross:
        if line.startswith(('BASH_', 'FILES_', 'SESSION', 'PROJECT_')) or not line.strip():
            in_cross = False
        elif line.strip() and line.strip() != 'none':
            cross_files.append(line.strip())

if not session_id or not source_key:
    print('ERROR: could not determine session or project key')
    sys.exit(1)

# Derive source project name from actual path on disk
_source_candidates = list(_reconstruct(source_key, None))
source_name = _source_candidates[0].name if _source_candidates else source_key.split('-')[-1]

# Group cross_files by target project key
targets: dict[str, dict] = {}
for f in cross_files:
    key, name = find_project_for_path(f)
    if key and key != source_key:
        proj_path = Path('/' + key.lstrip('-').replace('-', '/'))
        try:
            rel = str(Path(f).relative_to(proj_path))
        except ValueError:
            rel = Path(f).name
        if key not in targets:
            targets[key] = {'name': name, 'files': []}
        if rel not in targets[key]['files']:
            targets[key]['files'].append(rel)

if not targets:
    print('No cross-project references — .project-map unchanged')
    sys.exit(0)

# Load, update, write
projects = parse_map()
today = date.today().isoformat()

# Ensure source project is tracked
if source_key not in projects:
    projects[source_key] = {
        'name': source_name,
        'first_session': get_first_session(source_key),
        'refs': []
    }

# Add refs to each target project
for tkey, tinfo in targets.items():
    if tkey not in projects:
        _t_candidates = list(_reconstruct(tkey, None))
        _t_name = _t_candidates[0].name if _t_candidates else (tinfo['name'] or tkey.split('-')[-1])
        projects[tkey] = {
            'name': _t_name,
            'first_session': get_first_session(tkey),
            'refs': []
        }
    files_str = ', '.join(tinfo['files'])
    ref = f'{today} · {session_id[:8]} (from: {source_name}): {files_str}'
    if ref not in projects[tkey]['refs']:
        projects[tkey]['refs'].append(ref)

write_map(projects)
print(f'Updated .project-map — referenced {len(targets)} project(s): {", ".join(t["name"] for t in targets.values())}')
