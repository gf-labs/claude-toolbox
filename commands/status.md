---
description: Project status and recent Claude activity — git, BACKLOG, snapshot health
argument-hint: [--days N]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Multi-project status** (parent/global mode only):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-status.py

**Repo**:
!basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)"

**Branch and tracking**:
!git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo"

**Changes**:
!git status --short 2>/dev/null || echo "not a git repo"

**Recent commits**:
!git log --oneline -5 2>/dev/null || echo "none"

**Stash**:
!git stash list 2>/dev/null || echo "empty"

**CLAUDE.md**:
!test -f CLAUDE.md && echo "present" || echo "MISSING"

**BACKLOG.md (first 25 lines)**:
!head -25 BACKLOG.md 2>/dev/null || echo "not found"

**Recent Claude activity**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-history.py $ARGUMENTS

**Today**:
!date +%Y-%m-%d

---

## Your role

Render a concise project status snapshot using only the auto-collected context above. No preamble, no questions, no writes. One screen of output.

Use the **Scope** output to select the right format:
- **`SINGLE ...`** → use the single-project format below (use the git commands collected above)
- **`PARENT ...`** or **`GLOBAL`** → use the multi-project roll-up format below (use collect-status.py output)

If collect-status.py outputs `SINGLE [path]`, treat as single mode regardless.

For the history section: present collect-history.py output as-is — it is already formatted. If it is a single "No history..." line, show it without a section header.

In single mode, read the LAST_SNAPSHOT and SESSIONS_SINCE lines from collect-status.py output to populate the Last snapshot line.

---

## Output format

**Single mode:**
```
## Status — [repo] — [date]

**Branch:** [branch name] [ahead N / behind N / up to date / no remote]
**Changes:** [N staged, N unstaged] or "clean"
**Stash:** [N entries] or "empty"

**Recent commits:**
[5 lines from git log --oneline, as-is]

**CLAUDE.md:** present / MISSING

**Backlog:**
[In Progress: ... or "(nothing)"]
[Up Next: first item only, or "(nothing)"]

**Last snapshot:** [date from LAST_SNAPSHOT] [+(N) if SESSIONS_SINCE is not "—"] or "—"

---

**Recent Claude activity — last [N] days:**
[repo-name] — [YYYY-MM-DD]
  - [prompt]
  - ...
```

If not a git repo: skip git sections, note "(not a git repo)" at the top.
If no BACKLOG.md: omit the Backlog section entirely.
If LAST_SNAPSHOT is "—": show `Last snapshot: —`
If SESSIONS_SINCE is "—": show date only, no `(+N)`
If no history in range: `No Claude activity in the last [N] days.`

**Parent / global mode:**
```
## Status — [parent-path or "all projects"] — [N] projects — [date]

| Project | Branch | Changes | Last Commit | MEMORY.md | Backlog | Snapshot |
|---------|--------|---------|-------------|-----------|---------|----------|
| claude-toolbox | main | 2 | fa702a8 | 87L OK | 5 items | 2026-03-01 (+2) |
| ramp | main | — | a1b2c3d | 45L THIN | 2 items | 2026-02-20 |
| gfl-marketplace | main | — | 19fe86a | none | — | — |

---

**Recent Claude activity — last [N] days:**

### [repo-name] — [YYYY-MM-DD]
- [prompt]
...
```

Format collect-status.py tab-separated output into the table. Map columns:
- Changes: show count or "—" if zero
- MEMORY.md: combine MEMORY_LINES + MEMORY_STATUS (e.g. "87L OK", "none")
- Backlog: append "items" if count, else "—"
- Snapshot: show LAST_SNAPSHOT date; if SESSIONS_SINCE is not "—", append "(+N)" to flag unsaved sessions

Keep it tight — every line earns its place.
