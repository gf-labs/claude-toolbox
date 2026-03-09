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

**Session log**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py

**Plans**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py

**Plan map** (project associations):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plan-map.py

**Branch**:
!git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo"

**Changes**:
!git status --short 2>/dev/null || echo "clean"

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

Branch: [branch name] [ahead N / behind N / up to date / no remote]
Changes: [N files changed] or "clean"

In Progress: [first BACKLOG in-progress item] or "(nothing)"
Up Next: [first BACKLOG up-next item] or "(nothing)"

Last snapshot: [date] [+(N sessions) if SESSIONS_SINCE > 0] or "—"
Last session log: [date] ([N] entries) or "—"
Plans: [N active, N marked for cleanup] or "none"
MEMORY.md: [NL OK / THIN / WARN / MISSING]
```

**Parent/global mode:**

The Status data includes GROUP, PROJECT, BRANCH, LOCAL_BRANCHES, SESSIONS, CHANGES, LAST_COMMIT,
MEMORY_LINES, MEMORY_STATUS, BACKLOG_ITEMS, LAST_SNAPSHOT, SESSIONS_SINCE, LAST_SESSION_LOG, LOG_ENTRIES.

Render as follows:

1. **Group header rows** (GROUP=header): render as a bold section label with memory/session summary:
   `**gfl/** — 5 sessions, snapshot 2026-03-08`
   Then list child rows (GROUP=gfl) indented beneath it.

2. **Top-level rows** (GROUP=""): render in a flat table with columns:
   Project | Branch (Nbranches) | Sessions | Changes | Memory | Backlog | Snapshot | Log

3. **Child rows** (GROUP=parent_name): render indented under their parent group header,
   same columns as top-level.

4. **Stale section** (lines after `# STALE_KEYS` marker): render as:
   `**Stale keys** (N): key1 (note, N sessions), key2 (note) ...`
   These are project keys with no matching dir, duplicates, or the home-dir pseudo-project.

5. **Plans line** — combine Plans and Plan map data:
   `Plans: plan1.md (project, NL), plan2.md (project, NL) ...` or "none"

In parent/global mode, ignore the Branch and Changes auto-collected fields at the bottom
(they reflect the cwd which has no git repo).

---

## Constraints

- No history section — that's `/tools:status`
- No writes of any kind
- Haiku only — keep it fast
