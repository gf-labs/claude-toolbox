---
description: Capture current session context into project MEMORY.md
allowed-tools: Bash, Read, Write, Edit
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Migration check** (detects dated snapshot entries in MEMORY.md):
!python3 -c "
import re, os, sys
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT','') + '/scripts')
from _scope import get_scope
from pathlib import Path
mode, data, cwd = get_scope()
if mode == 'global' or cwd is None:
    try:
        import subprocess
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        key = git_root.replace('/', '-')
    except Exception:
        print('MIGRATION: none')
        sys.exit(0)
elif mode == 'single':
    key = data
else:
    key = str(cwd).replace('/', '-')
projects_dir = Path.home() / '.claude' / 'projects'
mem = projects_dir / key / 'memory' / 'MEMORY.md'
if not mem.exists():
    print('MIGRATION: none')
else:
    n = len(re.findall(r'^## Session snapshot —', mem.read_text(), re.MULTILINE))
    print(f'MIGRATION: {n} snapshot section(s) found' if n else 'MIGRATION: none')
    if n: print('MIGRATION_NEEDED: yes')
" 2>/dev/null || echo "MIGRATION: none"

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

## Migration (runs once if MIGRATION_NEEDED)

If MIGRATION_NEEDED is "yes":

Say: "MEMORY.md has [N] dated snapshot section(s) — these should move to session-log.md (unlimited history file). Migrate now? Reply `yes` or `skip`."

If yes:
1. Read MEMORY.md
2. Extract all `## Session snapshot — YYYY-MM-DD` blocks (each ends at the next `##` or EOF)
3. Convert each to session-log format: `## YYYY-MM-DD (migrated)\n[bullets]\n`
4. Append to session-log.md (create with `# [Repo] Session Log\n\n` header if missing)
5. Remove snapshot blocks from MEMORY.md (preserve all other content)
6. Report: "Migrated [N] snapshot(s) to session-log.md · MEMORY.md now [M] lines."

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
- Stable patterns, preferences, and conventions established
- Key architectural decisions that will affect future sessions
- Important file paths, commands, or configurations touched
- Anything a future session would need to know to continue effectively

Discard: ephemeral details, task mechanics, things already well-captured in existing MEMORY.md content.
Discard: session narrative (what was done today — that goes to session-log.md), git commit details, and event sequences.

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
