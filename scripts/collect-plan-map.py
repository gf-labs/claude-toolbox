#!/usr/bin/env python3
"""Scan Claude sessions for plan file references; write ## Plans section to .project-map.

Called by /tools:brief and /tools:wrap.
For each plan in ~/.claude/plans/*.md, tracks:
  - Created: date · session[:8] (project-name)  — chronologically first reference
  - Referenced: date · session[:8] (project-name) | ...  — subsequent sessions

Output (stdout): plan.md\tproject-display   (TSV for brief)
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import _reconstruct

MAP_FILE = Path.home() / '.claude' / 'plans' / '.project-map'
PROJECTS_DIR = Path.home() / '.claude' / 'projects'
PLANS_DIR = Path.home() / '.claude' / 'plans'


def _key_to_display(key: str) -> str:
    candidates = list(_reconstruct(key, None))
    if candidates:
        return candidates[0].name
    parts = [p for p in key.split('-') if p]
    return parts[-1] if parts else key


def _read_header_and_section() -> tuple[str, list[str]]:
    """Return (Plans-scanned value, lines inside ## Plans section)."""
    if not MAP_FILE.exists():
        return '', []
    lines = MAP_FILE.read_text(encoding='utf-8').splitlines()
    scanned = ''
    plan_lines = []
    in_plans = False
    for line in lines:
        if line.startswith('# Plans-scanned: '):
            scanned = line[17:].strip()
        if line.strip() == '## Plans':
            in_plans = True
            continue
        if in_plans and line.startswith('## ') and line.strip() != '## Plans':
            break
        if in_plans:
            plan_lines.append(line)
    return scanned, plan_lines


def _parse_plans_section() -> dict:
    """Parse ## Plans section → {plan_name: {created: str, refs: [str]}}"""
    _, plan_lines = _read_header_and_section()
    plans = {}
    current = None
    for line in plan_lines:
        if line.startswith('### '):
            current = line[4:].strip()
            plans[current] = {'created': '', 'refs': []}
        elif current and line.startswith('- Created: '):
            plans[current]['created'] = line[11:].strip()
        elif current and line.startswith('- Referenced: '):
            refs_str = line[14:].strip()
            if refs_str and refs_str != 'none':
                plans[current]['refs'] = [r.strip() for r in refs_str.split(' | ')]
    return plans


def _write_plans_section(plans: dict, scanned_ts: str):
    """Rewrite ## Plans section; preserve ## Projects section and file header."""
    existing_lines = MAP_FILE.read_text(encoding='utf-8').splitlines() if MAP_FILE.exists() else []
    kept = []
    in_plans = False
    for line in existing_lines:
        if line.strip() == '## Plans':
            in_plans = True
            continue
        if in_plans and line.startswith('## ') and line.strip() != '## Plans':
            in_plans = False
        if in_plans:
            continue
        if line.startswith('# Plans-scanned: '):
            continue
        kept.append(line)

    # Insert Plans-scanned header after other leading # comment lines
    insert_at = 0
    for i, line in enumerate(kept):
        if re.match(r'^#[^#]', line) or line == '#':
            insert_at = i + 1
        elif line.strip():
            break
    kept.insert(insert_at, f'# Plans-scanned: {scanned_ts}')

    # Strip trailing blanks
    while kept and not kept[-1].strip():
        kept.pop()

    plan_lines = ['', '## Plans', '']
    for name in sorted(plans):
        info = plans[name]
        plan_lines.append(f'### {name}')
        plan_lines.append(f"- Created: {info['created'] or 'unknown'}")
        refs = info.get('refs', [])
        if refs:
            plan_lines.append(f"- Referenced: {' | '.join(refs)}")
        else:
            plan_lines.append('- Referenced: none')
        plan_lines.append('')

    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAP_FILE.write_text('\n'.join(kept + plan_lines).strip() + '\n', encoding='utf-8')


def _load_renames() -> dict:
    """Return {old_name: current_name} from ~/.claude/plans/.renames, resolving chains."""
    renames_file = PLANS_DIR / '.renames'
    if not renames_file.exists():
        return {}
    raw = {}
    for line in renames_file.read_text(encoding='utf-8').splitlines():
        parts = line.strip().split('\t', 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            raw[parts[0]] = parts[1]
    # Resolve chains: a→b, b→c becomes a→c
    resolved = {}
    for old in raw:
        cur = old
        seen = {cur}
        while cur in raw and raw[cur] not in seen:
            cur = raw[cur]
            seen.add(cur)
        resolved[old] = cur
    return resolved


def _scan() -> tuple[dict, float]:
    """Scan all project JSONLs for plan file references.

    Returns (refs_by_plan, newest_mtime).
    refs_by_plan: {plan_name: [(session_mtime, session_id, project_key), ...]}
    """
    plan_names = {f.name for f in PLANS_DIR.glob('*.md')} if PLANS_DIR.exists() else set()
    refs_by_plan: dict[str, list] = {n: [] for n in plan_names}
    newest_mtime = 0.0
    renames = _load_renames()  # {old_name: current_name}

    for proj_dir in PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue
        project_key = proj_dir.name
        for jsonl in proj_dir.glob('*.jsonl'):
            mtime = jsonl.stat().st_mtime
            if mtime > newest_mtime:
                newest_mtime = mtime
            session_id = jsonl.stem
            try:
                content = jsonl.read_text(encoding='utf-8', errors='replace')
            except OSError as e:
                print(f'warning: could not read {jsonl}: {e}', file=sys.stderr)
                continue
            for line in content.splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get('type') != 'assistant':
                    continue
                items = obj.get('message', {}).get('content', [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or item.get('type') != 'tool_use':
                        continue
                    if item.get('name') not in ('Write', 'Edit', 'Read'):
                        continue
                    fp = item.get('input', {}).get('file_path', '')
                    if not fp:
                        continue
                    try:
                        p = Path(fp)
                        p.relative_to(PLANS_DIR)
                        pname = renames.get(p.name, p.name)  # resolve rename if applicable
                        if pname.endswith('.md') and pname in refs_by_plan:
                            refs_by_plan[pname].append((mtime, session_id, project_key))
                    except ValueError:
                        pass

    return refs_by_plan, newest_mtime


def _refs_to_plan_info(refs_by_plan: dict) -> dict:
    """Convert raw ref tuples to {plan_name: {created, refs}}."""
    result = {}
    for name, refs in refs_by_plan.items():
        if not refs:
            result[name] = {'created': '', 'refs': []}
            continue
        refs_sorted = sorted(refs, key=lambda r: r[0])
        c_mtime, c_sid, c_key = refs_sorted[0]
        c_date = datetime.fromtimestamp(c_mtime).date().isoformat()
        c_display = _key_to_display(c_key)
        created_str = f'{c_date} · {c_sid[:8]} ({c_display})'

        ref_strs = []
        seen = {c_sid}
        for mtime, sid, key in refs_sorted[1:]:
            if sid in seen:
                continue
            seen.add(sid)
            d = datetime.fromtimestamp(mtime).date().isoformat()
            display = _key_to_display(key)
            ref_strs.append(f'{d} · {sid[:8]} ({display})')
        result[name] = {'created': created_str, 'refs': ref_strs}
    return result


# --- Cache freshness check ---
# Key on newest plan file mtime (not JSONL mtime) so PostToolUse hook doesn't
# trigger a full scan on every Write to non-plan files.
scanned_ts, _ = _read_header_and_section()
needs_scan = True
if scanned_ts:
    try:
        cached_epoch = datetime.fromisoformat(scanned_ts).timestamp()
        newest_plan = max(
            (f.stat().st_mtime for f in PLANS_DIR.glob('*.md')),
            default=0.0
        ) if PLANS_DIR.exists() else 0.0
        needs_scan = newest_plan > cached_epoch
    except Exception:
        needs_scan = True

if needs_scan:
    refs_by_plan, newest_mtime = _scan()
    plan_info = _refs_to_plan_info(refs_by_plan)

    # For plans on disk with no scan results, keep existing cached info
    existing = _parse_plans_section()
    plan_names_on_disk = {f.name for f in PLANS_DIR.glob('*.md')} if PLANS_DIR.exists() else set()
    merged = {k: v for k, v in plan_info.items() if k in plan_names_on_disk}
    for name in plan_names_on_disk:
        if name not in merged and name in existing:
            merged[name] = existing[name]

    newest_plan_mtime = max(
        (f.stat().st_mtime for f in PLANS_DIR.glob('*.md')),
        default=0.0
    ) if PLANS_DIR.exists() else 0.0
    ts = datetime.fromtimestamp(newest_plan_mtime).isoformat(timespec='seconds') if newest_plan_mtime else ''
    _write_plans_section(merged, ts)
    plan_info = merged
else:
    plan_info = _parse_plans_section()

# --- Output TSV for brief ---
for name, info in sorted(plan_info.items()):
    created = info.get('created', '')
    project_display = '?'
    if '(' in created and created.endswith(')'):
        project_display = created[created.rfind('(') + 1:-1]
    print(f'{name}\t{project_display}')
