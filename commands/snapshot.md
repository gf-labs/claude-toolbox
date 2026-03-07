---
description: Capture current session context into project MEMORY.md
allowed-tools: Bash, Read, Write, Edit
---

## Auto-collected context

**Current project**:
!git rev-parse --show-toplevel 2>/dev/null || echo "(not a git repo)"

**Repo name**:
!basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(no repo)"

**Today**:
!date +%Y-%m-%d

**Current MEMORY.md**:
!python3 -c "
import os
from pathlib import Path

project = '$(git rev-parse --show-toplevel 2>/dev/null)'.strip()
if not project or project == '(not a git repo)':
    print('NO PROJECT')
else:
    # Derive project dir key the same way Claude Code does: replace / with -
    key = project.lstrip('/').replace('/', '-')
    mem = Path.home() / '.claude' / 'projects' / key / 'memory' / 'MEMORY.md'
    if mem.exists():
        print(f'PATH: {mem}')
        print(mem.read_text())
    else:
        print(f'PATH: {mem}')
        print('MISSING — will be created')
" 2>/dev/null || echo "Could not determine project"

**Recent git activity**:
!git log --oneline -10 2>/dev/null || echo "none"

**Staged/unstaged changes**:
!git status --short 2>/dev/null || echo "clean"

---

## Your role

You are capturing the current session's key context into MEMORY.md so it persists for future sessions. This is a write action — read the existing MEMORY.md content above, then append a new dated section with insights from this session.

---

## Steps

**Step 1 — Reflect on this session**

Look back at what was discussed and done in this conversation. Identify:
- Key decisions made (architectural, design, workflow)
- Problems solved and how
- Patterns established or discovered
- Important file paths, commands, or configurations touched
- Anything a future session would need to know to continue effectively

Discard: ephemeral details, task mechanics, things already well-captured in existing MEMORY.md content.

**Step 2 — Draft the snapshot**

Write a concise dated section. Target: 5–15 bullet points. Each bullet = one durable fact a future session needs.

Format:
```
## Session snapshot — [date]

- [key insight or decision]
- [key insight or decision]
...
```

Show the draft to the user before writing. Ask: "Add this to MEMORY.md? Reply `yes` to save, or tell me what to change."

**Step 3 — Write**

If user confirms: use the PATH shown in auto-collected context above.

- If MEMORY.md exists: append the new section at the end using Edit tool
- If MEMORY.md is MISSING: create it with Write tool, starting with `# [Repo] Memory\n\n` then the snapshot section

Confirm: "Saved to `[path]`."

---

## Constraints

- Never overwrite existing MEMORY.md content — append only
- Never fabricate details not discussed in this session
- If not in a git repo: say "No project detected — MEMORY.md is project-scoped. Run this from within a repo."
