---
description: Capture current session context into project MEMORY.md
allowed-tools: Bash, Read, Write, Edit
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Project MEMORY.md**:
!python3 -c "
import os, sys
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope
mode, data, cwd = get_scope()
from pathlib import Path
projects_dir = Path.home() / '.claude' / 'projects'

if mode == 'single':
    mem = projects_dir / data / 'memory' / 'MEMORY.md'
    print(f'PATH: {mem}')
    print(mem.read_text() if mem.exists() else 'MISSING — will be created')
elif mode == 'parent':
    print('PARENT MODE — see scope output for child projects')
else:
    # Global: try git fallback
    import subprocess
    git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
    key = git_root.replace('/', '-')
    mem = projects_dir / key / 'memory' / 'MEMORY.md'
    print(f'PATH: {mem}')
    print(mem.read_text() if mem.exists() else 'MISSING — will be created')
" 2>/dev/null || echo "Could not determine project"

**Recent git activity**:
!git log --oneline -10 2>/dev/null || echo "none"

**Staged/unstaged changes**:
!git status --short 2>/dev/null || echo "clean"

**Today**:
!date +%Y-%m-%d

---

## Your role

You are capturing the current session's key context into MEMORY.md so it persists for future sessions. This is a write action — read the existing MEMORY.md content above, then append a new dated section with insights from this session.

---

## Scope handling

Read the **Scope** output above and act accordingly:

- **`SINGLE [name] (key)`** — proceed directly using the MEMORY.md PATH shown above.

- **`PARENT [path] — N projects: [list]`** — snapshot targets one project per session. Ask:
  > "Multiple projects detected ([list]). Which project should this session be snapshotted to?"
  Once the user picks one, derive its key: `str(child_path).replace('/', '-')` and target that MEMORY.md.

- **`GLOBAL`** — snapshot is project-scoped. If git detected a repo above (PATH is shown), proceed with that. If no git repo and no single project: say "No project detected — run this from within a project directory."

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

Use the PATH shown in auto-collected context (or derived from user's project selection in parent mode).

- If MEMORY.md exists: append the new section at the end using Edit tool
- If MEMORY.md is MISSING: create it with Write tool, starting with `# [Repo] Memory\n\n` then the snapshot section

Confirm: "Saved to `[path]`."

---

## Constraints

- Never overwrite existing MEMORY.md content — append only
- Never fabricate details not discussed in this session
- Do not include ramp knowledge-graph, XP, or level details — those belong in /ramp:snapshot
- If not in a git repo and scope is global: say "No project detected — MEMORY.md is project-scoped. Run this from within a repo."
