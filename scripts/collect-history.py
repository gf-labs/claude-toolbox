#!/usr/bin/env python3
"""Cross-project history — recent prompts grouped by repo and date."""
import argparse, json, sys, time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from _scope import get_scope

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=7)
parser.add_argument('--project', type=str, default=None)
args, _ = parser.parse_known_args()

# Auto-detect scope if --project not explicitly passed
project_names = None  # multi-name filter (parent mode)
if not args.project:
    _mode, _scope_data, _scope_cwd = get_scope()
    if _mode == 'single':
        args.project = _scope_cwd.name
    elif _mode == 'parent':
        project_names = [c.name for _, c in _scope_data]

project_filter = args.project.lower() if args.project else None

history_file = Path.home() / '.claude' / 'history.jsonl'
if not history_file.exists():
    print('NO HISTORY FILE')
    sys.exit(0)

cutoff = time.time() - args.days * 86400
entries = []

with open(history_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            ts = obj.get('timestamp', 0) / 1000
            if ts < cutoff:
                continue
            project = obj.get('project', '')
            repo = project.split('/')[-1] if project else '(no repo)'
            if project_filter and project_filter not in repo.lower():
                continue
            if project_names and not any(name.lower() in repo.lower() for name in project_names):
                continue
            entries.append({
                'ts': ts,
                'repo': repo,
                'date': datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d'),
                'display': obj.get('display', '').replace('\n', ' ')[:100],
            })
        except Exception:
            continue

if not entries:
    msg = f'No history in the last {args.days} days'
    if project_filter:
        msg += f' for project matching "{project_filter}"'
    print(msg)
    sys.exit(0)

groups = defaultdict(list)
for e in sorted(entries, key=lambda x: x['ts'], reverse=True):
    key = (e['repo'], e['date'])
    groups[key].append(e['display'])

if project_filter:
    suffix = f' — {project_filter}'
elif project_names:
    suffix = f' — {", ".join(project_names)}'
else:
    suffix = ''
print(f'=== Last {args.days} days{suffix} ===')
print(f'Total: {len(entries)} prompts across {len(set(k[0] for k in groups))} project(s)')
print()

seen_keys = []
for key in sorted(groups.keys(), key=lambda k: k[1], reverse=True):
    if key not in seen_keys:
        seen_keys.append(key)
        repo, date = key
        print(f'### {repo} — {date}')
        for prompt in groups[key][:10]:
            print(f'  - {prompt}')
        if len(groups[key]) > 10:
            print(f'  ... and {len(groups[key]) - 10} more')
        print()
