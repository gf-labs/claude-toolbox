---
description: Summarize a session — given a session ID or path, returns a concise summary of what happened
argument-hint: [session-id | path] (default: most recent session)
allowed-tools: Bash, Read
---

## Arguments

`$ARGUMENTS`

Parse from arguments:
- **session-id** — 8+ hex chars, optionally a full UUID (e.g. `4794c719` or `4794c719-...`)
- **path** — absolute path to a `.jsonl` file
- **(none)** — default to the most recent session in the current project scope

---

## Step 1 — Resolve the JSONL path

Run the following to find the target file:

```bash
python3 -c "
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
try:
    from _scope import get_scope
    _m, _d, _ = get_scope()
    _allowed = {_d} if _m == 'single' else ({k for k, _ in _d} if _m == 'parent' else None)
except Exception:
    _allowed = None

arg = 'ARGUMENTS_PLACEHOLDER'.strip()
projects_dir = Path.home() / '.claude' / 'projects'

# Case 1: explicit path
if arg.startswith('/') and arg.endswith('.jsonl'):
    p = Path(arg)
    print(f'FOUND: {p}' if p.exists() else f'NOT_FOUND: {p}')
    sys.exit(0)

# Case 2: session ID prefix
if arg and len(arg) >= 8:
    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir(): continue
        if _allowed is not None and proj.name not in _allowed: continue
        for f in proj.glob('*.jsonl'):
            if f.stem.startswith(arg) or f.stem.replace('-','').startswith(arg):
                print(f'FOUND: {f}')
                sys.exit(0)
    print(f'NOT_FOUND: no session matching {arg!r}')
    sys.exit(0)

# Case 3: default — most recent session in scope
newest = None
newest_mtime = 0
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    if _allowed is not None and proj.name not in _allowed: continue
    for f in proj.glob('*.jsonl'):
        if f.stat().st_mtime > newest_mtime:
            newest_mtime = f.stat().st_mtime
            newest = f
if newest:
    print(f'FOUND: {newest}')
else:
    print('NOT_FOUND: no sessions in scope')
"
```

Replace `ARGUMENTS_PLACEHOLDER` with the raw `$ARGUMENTS` string.

If the output is `NOT_FOUND:` — say "Session not found: [detail]." and stop.

---

## Step 2 — Read the JSONL

Use the `Read` tool to read the resolved path. The file contains one JSON object per line.

Parse the following fields:
- `type: "custom-title"` → `customTitle` — session name
- `type: "user"` → first user message text (from `message.content`)
- `type: "summary"` → `summary` — compacted context summary if present
- `type: "assistant"` tool_use blocks → file paths written/edited, bash commands run, git commits visible in output
- Look for git commit messages in bash output lines containing `git commit`

---

## Step 3 — Output

```
## Session: [session-id first 8 chars] — [session name or "(untitled)"]
**Date**: [mtime date from file stat, or first entry date]
**Project**: [project name from file path]

**What happened** (3–6 bullets):
- [key action or decision]

**Files changed**: [comma-separated relative paths, or "none detected"]
**Commits**: [N commits — "subject of most recent", or "none detected"]
**Open threads**: [if any unresolved items visible] (omit section if none)
```

Keep it to one screen. Focus on decisions and outcomes, not mechanics.
