---
description: Cold-start session orientation — use when starting fresh or returning after a long absence (days or weeks). Scales depth to how long you've been away. Not for quick mid-session checks (use /tools:status) or planning (use /tools:overview).
argument-hint: [session-id | --days N]
allowed-tools: Bash, Read
model: claude-haiku-4-5-20251001
---

## Collect context

Run each command below now before producing output. Store results mentally.

**Scope**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
```

**Status**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-status.py
```

**Absence duration + resume point**:
```bash
python3 -c "
import os, re, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope, project_key
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'
if mode == 'single':
    key = data
else:
    import subprocess
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        key = project_key(git_root, projects_dir)
    except Exception:
        print('ABSENCE_DAYS: unknown')
        sys.exit(0)
log = projects_dir / key / 'memory' / 'session-log.md'
if not log.exists():
    print('ABSENCE_DAYS: unknown')
    sys.exit(0)
text = log.read_text()
dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
if not dates:
    print('ABSENCE_DAYS: unknown')
    sys.exit(0)
last = max(dates)
delta = (datetime.today().date() - datetime.strptime(last, '%Y-%m-%d').date()).days
print(f'ABSENCE_DAYS: {delta}')
print(f'LAST_SESSION_DATE: {last}')
blocks = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', text, flags=re.MULTILINE)
dated = [b for b in blocks if re.match(r'^## \d{4}-\d{2}-\d{2}', b)]
last_block = sorted(dated, key=lambda b: re.match(r'^## (\d{4}-\d{2}-\d{2})', b).group(1))[-1] if dated else ''
resume = re.search(r'^\*\*Resume:\*\* (.+)$', last_block, re.MULTILINE)
print(f'RESUME: {resume.group(1)}' if resume else 'RESUME: (none)')
"
```

**Session log** (metadata + recent entries — depth scales to absence):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py
```

**Plans** (with first bullet):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py
```

**Plan map** (project associations):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plan-map.py
```

**Branch, changes, commits, stash, CLAUDE.md, backlog, date**:
```bash
echo "BRANCH:" && (git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo")
echo "CHANGES:" && (git status --short 2>/dev/null || echo "clean")
echo "COMMITS:" && (git log --oneline -5 2>/dev/null || echo "none")
echo "STASH:" && (git stash list 2>/dev/null || echo "empty")
echo "CLAUDE_MD:" && (test -f CLAUDE.md && echo "present" || echo "MISSING")
REPO=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null)
DOMAIN=$(git rev-parse --show-toplevel 2>/dev/null | sed 's|.*/Repos/||' | cut -d'/' -f1)
TW_PROJECT="${DOMAIN}.${REPO}"
echo "IN_PROGRESS:" && (task rc.verbose=nothing project:${TW_PROJECT} +ACTIVE list 2>/dev/null || echo "(none)")
echo "UP_NEXT:" && (task rc.verbose=nothing project:${TW_PROJECT} limit:3 list 2>/dev/null || echo "(none)")
echo "DATE:" && date +%Y-%m-%d
```

**Current session**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py
```

**Recent Claude activity**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-history.py $ARGUMENTS
```

**Ramp — nodes due today**:
```bash
python3 -c "
import re
from datetime import date
from pathlib import Path
today = date.today().isoformat()
g = Path.home() / '.claude' / 'knowledge-graphs' / 'claude-code.md'
if not g.exists():
    print('no graph')
else:
    text = g.read_text()
    due = [m for m in re.findall(r'next: (\d{4}-\d{2}-\d{2})', text) if m <= today]
    level_match = re.search(r'^level: (.+)$', text, re.MULTILINE)
    xp_match = re.search(r'^xp: (\d+)$', text, re.MULTILINE)
    level = level_match.group(1) if level_match else '?'
    xp = xp_match.group(1) if xp_match else '?'
    print(f'{len(due)} nodes due  |  {level}  |  {xp} XP')
" 2>/dev/null || echo "no ramp graph"
```

**Phase / roadmap**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-phase.py 2>/dev/null || echo "NOT_FOUND"
```

**Toolbox env**:
```bash
printenv CLAUDE_TOOLBOX_ROOT 2>/dev/null && echo "(set)" || echo "NOT SET"
```

**Plugin drift**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plugin-drift.py 2>/dev/null || echo "unavailable"
```

**Unnamed sessions** (dry-run — proposes names, writes nothing):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/rename-unnamed.py --dry-run
```

**Project extension**:
```bash
cat .claude/status.md 2>/dev/null || echo "(no project extension)"
```

---

## Your role

**Mode detection:** Check `$ARGUMENTS` first. If it contains an 8+ character hex string (a session ID or UUID prefix), enter **Session Summary Mode** — ignore all auto-collected context above and do the following instead:

1. Locate the JSONL file:
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
arg = '$ARGUMENTS'.strip().split()[0]
projects_dir = Path.home() / '.claude' / 'projects'
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    if _allowed is not None and proj.name not in _allowed: continue
    for f in proj.glob('*.jsonl'):
        if f.stem.startswith(arg) or f.stem.replace('-','').startswith(arg):
            print(f'FOUND: {f}')
            sys.exit(0)
print(f'NOT_FOUND: {arg}')
"
```
2. If NOT_FOUND: say "Session not found: [id]." and stop.
3. Read the JSONL file. Parse: `custom-title`, first user message, tool_use blocks (files written/edited, bash commands, git commits visible in output), any `summary` type entries.
4. Output:
```
## Session: [first 8 chars] — [title or "(untitled)"]
**Date**: [mtime date]
**Project**: [project name from path]

**What happened** (3–6 bullets):
- [key action or decision]

**Files changed**: [comma-separated relative paths, or "none detected"]
**Commits**: [N commits — "subject of most recent", or "none detected"]
**Open threads**: [if any] (omit if none)
```

Otherwise (no session-id in arguments): Read-only orient command. Read the auto-collected context above and render a concise status summary. No questions, no writes. One screen.

**Depth scaling by absence:** Use ABSENCE_DAYS to tune output depth:
- **< 2 days** (warm): show last 1 session log entry, skip architecture snapshot, skip MEMORY.md content
- **2–7 days** (moderate): show last 3 session log entries, include architecture snapshot briefly
- **7+ days or unknown** (cold): show last 5 session log entries, full architecture snapshot, full MEMORY.md content

**Resume point:** If RESUME is not "(none)", surface it prominently at the top of the output as: `Resume: [text]`

If `.claude/status.md` content was injected above (not "(no project extension)"): insert those sections between Phase and MEMORY.md, replacing the `[Extension sections]` placeholder. Append any next-step bullets specified by the extension to any relevant section.

---

## Output format

**Single mode:**

```
## Brief — [repo] — [date]

Branch: [branch] [ahead N / behind N / up to date / no remote]
Changes: [list changed filenames, one per line, indented] or "clean"
Stash: [N entries] or "empty" (omit if empty)

Recent commits:
  [5 lines from git log --oneline]

CLAUDE.md: present / MISSING

In Progress: [first task from IN_PROGRESS] or "(nothing)"
Up Next: [top tasks from UP_NEXT, one per line indented] or "(nothing)"

This session: [SESSION first 8 chars] — [N files changed, or "no changes"]

Last snapshot: [date (N days ago)] [+(N sessions) if SESSIONS_SINCE > 0] or "—"
Last session log: [date (N days ago)] ([N] entries)
  - [entry 1 from RECENT_ENTRIES]
  - [entry 2]
  ... up to 5

Plans:
  plan1.md [project] — Title
    → first bullet
  plan2.md [project] — Title

Phase: [phase name from collect-phase.py] ([source file]) (omit entirely if NOT_FOUND)
  Blocker: [blocker text] (omit if no BLOCKER line)

[Extension sections]      ← insert here if .claude/status.md was loaded; omit if no extension

MEMORY.md: [NL OK / THIN / WARN / MISSING]
  [first 8–10 lines of content if present, indented]

Ramp: [N] nodes due  |  [Level]  |  [XP] XP  (run /tools:status for full detail)
Toolbox: CLAUDE_TOOLBOX_ROOT [set / NOT SET] · plugins: [in sync / N stale / N missing / unavailable]
Unnamed sessions (proposals — /tools:pin applies): [id8 → name, one per "PROPOSAL:" line] (omit line entirely if NONE)

---

Recent Claude activity — last [N] days:
[repo-name] — [YYYY-MM-DD]
  - [prompt]
  - ...
```

If no history in range: `No Claude activity in the last [N] days.` (no section header needed)

**Elapsed time**: wherever a date appears, append `(today)`, `(yesterday)`, or `(N days ago)` by comparing to today's date. Do not show elapsed for "—".

**Parent/global mode:**

The Status data includes GROUP, PROJECT, BRANCH, LOCAL_BRANCHES, SESSIONS, CHANGES, LAST_COMMIT,
MEMORY_LINES, MEMORY_STATUS, BACKLOG_ITEMS, LAST_SNAPSHOT, SESSIONS_SINCE, LAST_SESSION_LOG, LOG_ENTRIES.

Render as follows:

1. **Group header rows** (GROUP=header): bold section label:
   `**gfl/** — 4 sessions`
   Then list child rows (GROUP=gfl) beneath it.

2. **Top-level and child rows**: table with columns:
   Project | Branch | Sessions | Changes | Last Commit | Memory | Backlog | Snapshot | Log

3. **Orphaned keys** (lines after `# ORPHANED_KEYS` marker):
   `**Orphaned** (N): key1 (note, N sessions) ...` — no dir on disk, safe to delete with /cleanup

4. **Unscoped keys** (lines after `# UNSCOPED_KEYS` marker):
   `**Unscoped** (N sessions): N sessions with no project scope — run /done inside those sessions or /cleanup delete-me`

5. **Project Summaries** — for every project row that has any of: SESSIONS > 0, LOG date present, CHANGES > 0. Skip rows where all three are absent.
   ```
   **[project]** · [branch] · [N sessions] · [N backlog] · Memory: [status]
     [1–2 sentences: what was done last (from ENTRIES: block) + what's in flight (from associated plans)]
     Flags: [comma list of any: "N uncommitted", "WARN memory", "THIN memory", "no snapshot", "MISSING memory"] (omit line if none)
   ```
   Source the narrative from the ENTRIES: block for this project in session log output, plus plan titles associated with this project from plan-map data. Max 2 body lines per project.

6. **Plans block** — use Plans + Plan map data:
   ```
   Plans:
     plan1.md [project] — Title
       → first bullet
   ```

7. **Last active block** — find the project with the most recent ENTRIES: block in Session log output.
   Show its entries:
   ```
   Last active: [project] ([date, N days ago])
     - entry 1
     - entry 2
     ...
   ```

8. **Toolbox line**: `Toolbox: CLAUDE_TOOLBOX_ROOT [set / NOT SET] · plugins: [in sync / N stale / N missing / unavailable]`

9. **Ramp line**: show the ramp due-nodes line from auto-collected context.

10. **Recent Claude activity** — from collect-history.py, at the bottom:
   ```
   ---

   Recent Claude activity — last [N] days:

   ### [repo-name] — [YYYY-MM-DD]
   - [prompt]
   ...
   ```
   If no history: `No Claude activity in the last [N] days.`

**Elapsed time**: apply `(today)` / `(yesterday)` / `(N days ago)` to all dates in parent mode too.

In parent/global mode, ignore the Branch, Changed files, Recent commits, and Stash blocks (they reflect cwd which has no git repo).

---

## Constraints

- No writes of any kind
- Haiku only — keep it fast
