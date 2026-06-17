---
description: Search session history by keyword — returns matching sessions with title and prompts
argument-hint: <pattern> [--days N]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Arguments

`$ARGUMENTS`

Parse from arguments:
- **Positional pattern** (any word not starting with `--`) — required. Case-insensitive substring match against session title, first user message, and last-prompt content.
- `--days N` — limit search to sessions from the last N days (default: no limit)

If no pattern is provided: say "Usage: /tools:search-sessions <pattern> [--days N]" and stop.

---

## Your role

Read-only session search. Find matching sessions and display them — no deletion.

**Step 1 — Search:**

```bash
python3 -c "
import json, os, sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
try:
    from _scope import get_scope
    _m, _d, _ = get_scope()
    _allowed = {_d} if _m == 'single' else ({k for k, _ in _d} if _m == 'parent' else None)
except Exception:
    _allowed = None

args = 'ARGUMENTS_PLACEHOLDER'.split()
pattern = ''
days = None
i = 0
while i < len(args):
    if args[i] == '--days' and i + 1 < len(args):
        days = int(args[i+1]); i += 2
    else:
        pattern += (' ' if pattern else '') + args[i]; i += 1
pattern = pattern.lower()
cutoff = (datetime.now() - timedelta(days=days)).timestamp() if days else 0

projects_dir = Path.home() / '.claude' / 'projects'
results = []

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    if _allowed is not None and proj.name not in _allowed: continue
    for f in sorted(proj.glob('*.jsonl')):
        if days and f.stat().st_mtime < cutoff: continue
        try:
            custom_title = first_user = last_prompt = ''
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip(): continue
                obj = json.loads(line)
                t = obj.get('type', '')
                if t == 'custom-title':
                    custom_title = obj.get('customTitle', '')
                if t == 'last-prompt' and not last_prompt:
                    last_prompt = obj.get('lastPrompt', '')[:120]
                if t == 'user' and not first_user:
                    msg = obj.get('message', {})
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get('type') == 'text':
                                first_user = c.get('text', '')[:120]; break
                    elif isinstance(content, str):
                        first_user = content[:120]
            searchable = (custom_title + ' ' + first_user + ' ' + last_prompt).lower()
            if pattern in searchable:
                from datetime import date
                age_days = (datetime.now().timestamp() - f.stat().st_mtime) / 86400
                print(f'MATCH|{proj.name}|{f.stem[:8]}|{int(age_days)}d|{f.stat().st_size//1024}K|{custom_title or \"(untitled)\"}|{first_user[:80]}')
        except Exception:
            pass
"
```

Replace `ARGUMENTS_PLACEHOLDER` with the raw arguments string.

**Step 2 — Display results:**

```
### Sessions matching "[pattern]" — [N] match(es)

| Session | Project | Age | Size | Title | First message |
|---------|---------|-----|------|-------|---------------|
| 4794c719 | claude-toolbox | 3d | 45K | bug-report-... | "can you help me..." |
...
```

If no matches: "No sessions found matching '[pattern]'."

Omit the age/days qualifier in the header if `--days` was not provided.
