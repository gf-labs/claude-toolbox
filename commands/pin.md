---
description: Break checkpoint — status display, session log, optional MEMORY.md update
allowed-tools: Bash, Read, Write, Edit
model: claude-sonnet-4-6
---

## Collect context

Run each command below now before proceeding. Store results mentally.

**Scope**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
```

**Status**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-status.py
```

**Session log status**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py
```

**Branch, changes, backlog, date**:
```bash
echo "BRANCH:" && (git branch -vv 2>/dev/null | grep '^\*' || echo "not a git repo")
echo "CHANGES:" && (git status --short 2>/dev/null || echo "clean")
echo "BACKLOG:" && (head -25 BACKLOG.md 2>/dev/null || echo "not found")
echo "DATE:" && date +%Y-%m-%d
```

**Plans**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py
```

**Session activity**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py
```

**Session title**:
```bash
python3 -c "
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope
mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'
if mode == 'single':
    proj_dir = projects_dir / data
else:
    import subprocess
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        proj_dir = projects_dir / git_root.replace('/', '-')
    except Exception:
        print('TITLE: (untitled)')
        sys.exit(0)
jsonl_files = list(proj_dir.glob('*.jsonl'))
if not jsonl_files:
    print('TITLE: (untitled)')
    sys.exit(0)
current = max(jsonl_files, key=lambda f: f.stat().st_mtime)
title = ''
for line in current.read_text(errors='replace').splitlines():
    if not line.strip(): continue
    try:
        obj = json.loads(line)
        if obj.get('type') == 'custom-title':
            title = obj.get('customTitle', '')
    except Exception:
        continue
print(f'TITLE: {title or \"(untitled)\"}')
"
```

**Git log and diff**:
```bash
echo "GIT_LOG:" && (git log --oneline -10 2>/dev/null || echo "none")
echo "GIT_DIFF_STAT:" && (git diff HEAD --stat 2>/dev/null || echo "none")
```

**session-log.md**:
```bash
python3 -c "
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
"
```

**Migration check**:
```bash
python3 -c "
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
"
```

**Project MEMORY.md**:
```bash
python3 -c "
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
"
```

---

## Your role

Break checkpoint assistant. Work through the steps below. Step 1 is display-only — proceed immediately. Steps 2 and 3 are interactive — wait for the user's reply before proceeding.

---

## Step 0 — Ramp check

Check the current session's conversation history:
- If `/ramp:pin` was run as the previous (or a recent) user message: proceed silently to Step 1.
- If `/ramp:pin` has NOT been run this session: run it now automatically before continuing. Say: "Running `/ramp:pin` first…" then invoke the ramp:pin flow.
- If ramp is not installed (no `/ramp:pin` command available): skip silently and proceed to Step 1.

---

## Step 1 — Status (display only)

Read the auto-collected context and render:

```
## Pin — [repo] — [date]

Branch: [branch name] [ahead N / behind N / up to date / no remote]
Changes: [N files changed, listed] or "clean"

In Progress: [first BACKLOG in-progress item] or "(nothing)"
Up Next: [first BACKLOG up-next item] or "(nothing)"
Plans: [N active, N marked for cleanup] or "none"

Last snapshot: [date] [+(N sessions) if SESSIONS_SINCE > 0] or "—"
Last session log: [date] ([N] entries) or "—"

---

### This session — [SESSION first 8 chars] · [TITLE]

**What happened:**
- [3–8 bullets synthesized from FILES_TOUCHED, git log, and this conversation's activity]

**Files changed:** [comma-separated from FILES_TOUCHED, or "none"]
**Git:** [N commit(s) — "message of most recent"] or "none"
**Open threads:** [unresolved items visible in the conversation] (omit if none)
```

"What happened" synthesis rules:
- Lead with intent (what the user was trying to do), then actions taken
- Include any diagnosis/root cause work, not just the fix
- Group related changes into single bullets rather than listing every file
- Omit if FILES_TOUCHED is "none" and no git activity — say "No file changes this session"

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
   **What didn't work:** [failed approach — "tried X, failed because Y"] (omit if none)
   **Resume:** [exact next step to take when picking this up] (omit if nothing in flight)
   **Open threads:** [blocker or deferred item] (omit section entirely if none)
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

Then automatically capture stable patterns in MEMORY.md (no prompt needed):
1. Look back at this conversation. Identify durable facts: key decisions, stable patterns, important file paths, conventions, architectural choices — anything a future session needs. Discard session narrative (that belongs in session-log), git commit details, and ephemeral mechanics.
2. Draft a concise dated section (5–15 bullets):
   ```
   ## Session snapshot — [date] · [first 8 chars of SESSION id]

   - [key insight or decision]
   - [key insight or decision]
   ...
   ```
3. Show the draft to the user for awareness, then immediately append to MEMORY.md using the PATH shown in **Project MEMORY.md** context above — no confirmation needed.
   - If MISSING: create with Write tool using `# [Repo] Memory\n\n` header
   - If exists: append with Edit tool
4. Report: "MEMORY.md updated ([N] lines)."

Constraints:
- Never overwrite existing MEMORY.md content — append only
- Never fabricate details not discussed in this session
- Do not include ramp knowledge-graph, XP, or level details — those belong in /ramp:snapshot
- If not in a git repo and scope is global: say "No project detected — MEMORY.md is project-scoped. Run this from within a repo."
