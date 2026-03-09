---
description: Start-of-session orientation — branch, backlog, snapshot health, plans
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Status**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-status.py

**Session log** (metadata + last 5 entries from most recent session):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py

**Plans** (with first bullet):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py

**Plan map** (project associations):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plan-map.py

**Branch**:
!git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo"

**Changed files**:
!git status --short 2>/dev/null || echo "clean"

**MEMORY.md** (first 12 lines):
!head -12 MEMORY.md 2>/dev/null || echo "MISSING"

**Ramp — nodes due today**:
!python3 -c "
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

**Today**:
!date +%Y-%m-%d

---

## Your role

Read-only orient command. Read the auto-collected context above and render a concise status summary. No questions, no writes. One screen.

---

## Output format

**Single mode:**

```
## Brief — [repo] — [date]

Branch: [branch] [ahead N / behind N / up to date / no remote]
Changes: [list changed filenames, one per line, indented] or "clean"

In Progress: [first BACKLOG in-progress item] or "(nothing)"
Up Next: [first BACKLOG up-next item] or "(nothing)"

Last snapshot: [date (N days ago)] [+(N sessions) if SESSIONS_SINCE > 0] or "—"
Last session log: [date (N days ago)] ([N] entries)
  - [entry 1 from RECENT_ENTRIES]
  - [entry 2]
  ... up to 5

Plans:
  plan1.md [project] — Title
    → first bullet
  plan2.md [project] — Title

MEMORY.md: [NL OK / THIN / WARN / MISSING]
  [first 8–10 lines of content if present, indented]

Ramp: [N] nodes due  |  [Level]  |  [XP] XP
```

**Elapsed time**: wherever a date appears, append `(today)`, `(yesterday)`, or `(N days ago)` by comparing to today's date. Do not show elapsed for "—".

**Parent/global mode:**

The Status data includes GROUP, PROJECT, BRANCH, LOCAL_BRANCHES, SESSIONS, CHANGES, LAST_COMMIT,
MEMORY_LINES, MEMORY_STATUS, BACKLOG_ITEMS, LAST_SNAPSHOT, SESSIONS_SINCE, LAST_SESSION_LOG, LOG_ENTRIES.

Render as follows:

1. **Group header rows** (GROUP=header): bold section label:
   `**gfl/** — 4 sessions`
   Then list child rows (GROUP=gfl) beneath it.

2. **Top-level and child rows**: table with columns:
   Project | Branch | Sessions | Changes | Memory | Backlog | Snapshot | Log

3. **Orphaned keys** (lines after `# ORPHANED_KEYS` marker):
   `**Orphaned** (N): key1 (note, N sessions) ...` — no dir on disk, safe to delete with /cleanup

4. **Unscoped keys** (lines after `# UNSCOPED_KEYS` marker):
   `**Unscoped** (N sessions): N sessions with no project scope — run /done inside those sessions or /cleanup delete-me`

5. **Plans block** — use Plans + Plan map data:
   ```
   Plans:
     plan1.md [project] — Title
       → first bullet
   ```

6. **Last active block** — find the project with the most recent ENTRIES: block in Session log output.
   Show its entries:
   ```
   Last active: [project] ([date, N days ago])
     - entry 1
     - entry 2
     ...
   ```

7. **Ramp line**: show the ramp due-nodes line from auto-collected context.

**Elapsed time**: apply `(today)` / `(yesterday)` / `(N days ago)` to all dates in parent mode too.

In parent/global mode, ignore the Branch and Changed files blocks (they reflect cwd which has no git repo).

---

## Constraints

- No history section — that's `/tools:status`
- No writes of any kind
- Haiku only — keep it fast
