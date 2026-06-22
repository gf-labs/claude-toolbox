---
description: Time-windowed "where was I?" — git commits, session notes, and files touched in the last N hours or days. Use after stepping away for a few hours or days. Not for cold starts after a long absence (use /tools:brief) or live development checks (use /tools:status).
argument-hint: [--days N | --hours N]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Arguments

`$ARGUMENTS`

Parse `--days N` or `--hours N` from arguments. **Default: current session (no time window).** If `--hours N` is given, convert to fractional days (hours / 24). `--days` takes precedence over `--hours` if both are given.

Determine mode before running any commands:
- If no `--days` or `--hours` args → **session mode**
- If `--days` or `--hours` present → **time-window mode**

---

## Collect context

Run all commands now before producing output.

**Scope + date:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
date +%Y-%m-%d
```

**Current session (always run):**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py
```

**Git branch + uncommitted state:**
```bash
git branch -vv 2>/dev/null | head -1
git status --short 2>/dev/null | head -10
```

**Git commits — time-window mode only** (skip if session mode):
```bash
python3 -c "
from datetime import datetime, timedelta
import subprocess, sys
args = '$ARGUMENTS'.split()
days = None
for i, a in enumerate(args):
    if a == '--days' and i+1 < len(args):
        days = int(args[i+1]); break
    elif a == '--hours' and i+1 < len(args):
        days = int(args[i+1]) / 24; break
if days is None:
    print('(session mode — see git state above)')
    sys.exit(0)
since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')
result = subprocess.run(['git', 'log', '--oneline', '--since', since], capture_output=True, text=True)
print(result.stdout or '(no commits in window)')
"
```

**Files changed — time-window mode only** (skip if session mode; session mode uses FILES_TOUCHED above):
```bash
python3 -c "
from datetime import datetime, timedelta
import subprocess, sys
args = '$ARGUMENTS'.split()
days = None
for i, a in enumerate(args):
    if a == '--days' and i+1 < len(args):
        days = int(args[i+1]); break
    elif a == '--hours' and i+1 < len(args):
        days = int(args[i+1]) / 24; break
if days is None:
    print('(session mode — see FILES_TOUCHED above)')
    sys.exit(0)
since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')
result = subprocess.run(['git', 'log', '--name-only', '--pretty=format:', '--since', since], capture_output=True, text=True)
files = sorted(set(f for f in result.stdout.splitlines() if f.strip()))
print('\n'.join(files) if files else '(none)')
"
```

**Session log entries:**
```bash
python3 -c "
import os, re, sys, subprocess
from datetime import datetime, timedelta
from pathlib import Path
args = '$ARGUMENTS'.split()
days = None
for i, a in enumerate(args):
    if a == '--days' and i+1 < len(args):
        days = int(args[i+1]); break
    elif a == '--hours' and i+1 < len(args):
        days = int(args[i+1]) / 24; break

sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope, project_key
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'
if mode == 'single':
    key = data
else:
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        key = project_key(git_root, projects_dir)
    except Exception:
        print('(could not determine project)')
        sys.exit(0)
log = projects_dir / key / 'memory' / 'session-log.md'
if not log.exists():
    print('(no session log)')
    sys.exit(0)
text = log.read_text()
blocks = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', text, flags=re.MULTILINE)

if days is None:
    # Session mode: filter by current session ID
    result = subprocess.run(['python3', os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts/collect-summarize.py'],
                            capture_output=True, text=True)
    session_id = ''
    for line in result.stdout.splitlines():
        if line.startswith('SESSION:'):
            session_id = line.split(':', 1)[1].strip()[:8]
            break
    if not session_id:
        print('(could not determine session ID)')
        sys.exit(0)
    matched = [b for b in blocks if session_id in b]
    print('\n'.join(matched) if matched else '(no log entries yet this session)')
else:
    # Time-window mode: filter by date
    cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
    recent = [b for b in blocks if re.match(r'^## (\d{4}-\d{2}-\d{2})', b) and re.match(r'^## (\d{4}-\d{2}-\d{2})', b).group(1) >= cutoff]
    print('\n'.join(recent) if recent else '(no entries in window)')
"
```

---

## Your role

Produce a concise "where was I?" summary for the current project.
- **Session mode**: scope is the current Claude Code session only.
- **Time-window mode**: scope is the specified window.

This is not a status report — it's a re-orientation aid. Lead with what matters for picking up where you left off.

---

## Output format

**[repo] — this session — [date]**  (session mode)
**[repo] — last [N] day(s) / [N] hour(s) — [date]**  (time-window mode)

**Commits** — session mode: summarize staged/unstaged state from git status (e.g. "82 files modified, nothing staged"). Time-window mode: list from git log, grouped by theme if more than 3. If none: "(no commits)".

**Files touched** — session mode: FILES_TOUCHED from collect-summarize.py, comma-separated. Time-window mode: from git log. Omit generated/cache files. If none: "(none)".

**Session notes** — bullets extracted from session log entries. Focus on decisions, open threads, and resume points. Skip mechanics. (Session-log entries are date-stamped, not timestamped, so an `--hours` window still includes the full current day's notes — commits/files honor the sub-day window, notes are day-resolution.)

**Pick up here** — one sentence: the most actionable next step based on the evidence above. If there are open threads in the session log, surface the most recent one.
