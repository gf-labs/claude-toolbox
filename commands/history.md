---
description: Cross-project Claude history — what did I work on recently?
argument-hint: [--days N] [--project repo-name]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Arguments

`$ARGUMENTS`

Parse: `--days N` sets time range (default: 7). `--project name` filters to one project by matching the repo name at the end of the project path.

## Auto-collected context

**History** (prompts from the last N days, grouped):
!python3 -c "
import json, sys, time, re
from pathlib import Path
from datetime import datetime, timezone

raw_args = '$ARGUMENTS'
days = 7
project_filter = None

# Parse --days N
m = re.search(r'--days\s+(\d+)', raw_args)
if m:
    days = int(m.group(1))

# Parse --project name
m = re.search(r'--project\s+(\S+)', raw_args)
if m:
    project_filter = m.group(1).lower()

history_file = Path.home() / '.claude' / 'history.jsonl'
if not history_file.exists():
    print('NO HISTORY FILE')
    sys.exit(0)

cutoff = time.time() - days * 86400
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
            entries.append({
                'ts': ts,
                'repo': repo,
                'date': datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d'),
                'display': obj.get('display', '').replace('\n', ' ')[:100]
            })
        except Exception:
            continue

if not entries:
    print(f'No history in the last {days} days' + (f' for project matching \"{project_filter}\"' if project_filter else ''))
    sys.exit(0)

# Group by repo + date
from collections import defaultdict
groups = defaultdict(list)
for e in sorted(entries, key=lambda x: x['ts'], reverse=True):
    key = (e['repo'], e['date'])
    groups[key].append(e['display'])

print(f'=== Last {days} days{\" — \" + project_filter if project_filter else \"\"} ===')
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
"

---

## Your role

Read the auto-collected history above and render it as a clean, scannable report. Do not add analysis or commentary — just format and present what was injected. If the Python output already includes the formatted result, display it as-is.

The output should look like:

```
## History — last [N] days[  — [project filter]]

[N] prompts across [N] project(s)

### [repo-name] — [YYYY-MM-DD]
- [prompt, truncated]
- ...

### [repo-name] — [YYYY-MM-DD]
- ...
```

If no history was found: say so clearly and suggest running with fewer `--days`.
