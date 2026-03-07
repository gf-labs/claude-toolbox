---
description: Project status — git state, recent commits, BACKLOG, and knowledge tree health
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Auto-collected context

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

**Knowledge tree**:
!for f in ~/.claude/knowledge-graphs/*.md; do [ -f "$f" ] && head -8 "$f" && echo "---"; done 2>/dev/null || echo "none"

**Today**:
!date +%Y-%m-%d

---

## Your role

Render a concise project status snapshot using only the auto-collected context above. No preamble, no questions, no writes. One screen of output.

---

## Output format

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

**Knowledge tree:** [topic] · Level: [level] · [XP] XP · updated [date]
```

If not a git repo: skip git sections, note "(not a git repo)" at the top.
If no BACKLOG.md: omit the Backlog section entirely.
If no knowledge tree: show "none — run /ramp:up to create one".

Keep it tight — every line earns its place.
