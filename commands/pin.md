---
description: Break checkpoint — status display, session log, optional MEMORY.md update
allowed-tools: Bash, Read, Write, Edit
model: claude-sonnet-4-6
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Status**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-status.py

**Session log status**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py

**Branch**:
!git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo"

**Changes**:
!git status --short 2>/dev/null || echo "clean"

**BACKLOG.md (first 25 lines)**:
!head -25 BACKLOG.md 2>/dev/null || echo "not found"

**Plans**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py

**Session activity**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py

**Git log**:
!git log --oneline -10 2>/dev/null || echo "none"

**Git diff stat**:
!git diff HEAD --stat 2>/dev/null || echo "none"

**session-log.md**:
!python3 -c "
import os, sys
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope
from pathlib import Path
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'
if mode == 'single':
    key = data
else:
    import subprocess
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        key = git_root.replace('/', '-')
    except Exception:
        print('ERROR: Could not determine project key')
        exit(1)
log = projects_dir / key / 'memory' / 'session-log.md'
print(f'PATH: {log}')
print(log.read_text() if log.exists() else 'MISSING — will be created on first save')
" 2>/dev/null || echo "Could not determine project"

**Migration check**:
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
    import subprocess
    git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
    key = git_root.replace('/', '-')
    mem = projects_dir / key / 'memory' / 'MEMORY.md'
    print(f'PATH: {mem}')
    print(mem.read_text() if mem.exists() else 'MISSING — will be created')
" 2>/dev/null || echo "Could not determine project"

**Today**:
!date +%Y-%m-%d

---

## Your role

Break checkpoint assistant. Work through the steps below. Step 1 is display-only — proceed immediately. Steps 2 and 3 are interactive — wait for the user's reply before proceeding.

---

## Step 1 — Status (display only)

Read the auto-collected context and render:

```
## Pin — [repo] — [date]

Branch: [branch name] [ahead N / behind N / up to date / no remote]
Changes: [N files] or "clean"

In Progress: [first BACKLOG in-progress item] or "(nothing)"
Up Next: [first BACKLOG up-next item] or "(nothing)"
Plans: [N active, N marked for cleanup] or "none"

Last snapshot: [date] [+(N sessions) if SESSIONS_SINCE > 0] or "—"
Last session log: [date] ([N] entries) or "—"
```

No questions — display and proceed immediately to Step 2.

---

## Step 2 — Session log

Run the summarize flow using session activity, git log, and git diff stat collected above:

**Before drafting:** check **session-log.md** for any prior entry whose header contains the first 8 chars of SESSION (from collect-summarize.py). If a matching entry exists, this is a repeat pin in the same session — draft only the *new* activity since that entry (cross-reference its bullets to avoid duplication), and suffix the header with ` (2)`, ` (3)`, etc.

1. Draft a structured entry:
   ```
   ## [date] · [first 8 chars of SESSION id from collect-summarize.py]
   **Files changed:** [comma-separated relative paths, or "none"]
   **Git:** [N commit(s) — "message of most recent"] or "none"
   - [key action or decision — 3–8 bullets]
   **Open threads:** [item] (omit section entirely if none)
   ```
2. Show the draft. Ask: "Save to session-log.md? Reply `yes` or edit inline."
3. On confirm: append to the PATH shown in **session-log.md** context above.
   - If MISSING: create with Write tool using `# [Repo] Session Log\n\n` header
   - If exists: append with Edit tool (match last chars of existing content, append `\n\n` + entry)
4. Cross-project: for each path in CROSS_PROJECT_FILES, append an attributed entry to that project's session-log.md (infer owning project from the absolute path prefix):
   ```
   ## [date] · [8-char session id] [← source-repo]
   **Cross-project work from [source-repo] session:**
   - [specific files/actions in this project]
   ```

Constraints:
- Append only — never overwrite existing entries
- Do NOT write to MEMORY.md — session history belongs in session-log.md only
- If FILES_TOUCHED is "none": note "No file changes detected" in the entry body

After saving the session log, auto-name the session if it has no existing custom-title:
- Derive a short name from: the most recent git commit subject (strip "feat:", "fix:", "chore:"
  prefixes and trailing "(vX.Y.Z)"), or from FILES_TOUCHED if no commits (primary dir/file)
- Format: kebab-case, max 5 words, no dates, no generic words like "session" or "work"
- Examples: `plan-map-refactor`, `brief-enhancements`, `dotfiles-plugin-fix`
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/name-session.py "[derived-name]"
```
(Skips silently if already named.)

Then rename any other unnamed sessions in scope, passing the current session ID to skip it:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/rename-unnamed.py --skip [SESSION_id_from_collect-summarize]
```
If output contains RENAMED lines, append a compact note to your response: `Renamed: id→name, id→name`

After the session log is saved and named, tell the user:
> Context saved. Run `/compact` to compress the window.

---

## Step 3 — Stable patterns (optional)

If MIGRATION_NEEDED is "yes": run the migration flow first —
1. Read MEMORY.md
2. Extract all `## Session snapshot — YYYY-MM-DD` blocks (each ends at the next `##` or EOF)
3. Convert each to session-log format: `## YYYY-MM-DD (migrated)\n[bullets]\n`
4. Append to session-log.md (create with header if missing)
5. Remove snapshot blocks from MEMORY.md (preserve all other content)
6. Report: "Migrated [N] snapshot(s) to session-log.md · MEMORY.md now [M] lines."

Then ask: "Also capture stable patterns in MEMORY.md? Reply `yes` or `skip`."

If `yes`:
1. Look back at this conversation. Identify durable facts: key decisions, stable patterns, important file paths, conventions, architectural choices — anything a future session needs. Discard session narrative (that belongs in session-log), git commit details, and ephemeral mechanics.
2. Draft a concise dated section (5–15 bullets):
   ```
   ## Session snapshot — [date]

   - [key insight or decision]
   - [key insight or decision]
   ...
   ```
3. Show the draft. Ask: "Add this to MEMORY.md? Reply `yes` or tell me what to change."
4. On confirm: append to MEMORY.md using the PATH shown in **Project MEMORY.md** context above.
   - If MISSING: create with Write tool using `# [Repo] Memory\n\n` header
   - If exists: append with Edit tool

Constraints:
- Never overwrite existing MEMORY.md content — append only
- Never fabricate details not discussed in this session
- Do not include ramp knowledge-graph, XP, or level details — those belong in /ramp:snapshot
- If not in a git repo and scope is global: say "No project detected — MEMORY.md is project-scoped. Run this from within a repo."
