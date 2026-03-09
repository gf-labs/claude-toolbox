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

Same roll-up table as `status` but without the history section — just Branch, Changes, MEMORY.md, Backlog, Snapshot, Log columns. Source: `collect-status.py`.

---

## Constraints

- No history section — that's `/tools:status`
- No writes of any kind
- Haiku only — keep it fast
