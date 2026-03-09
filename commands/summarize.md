---
description: Summarize the current session and append to session-log.md
allowed-tools: Bash, Read, Write, Edit
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Session activity**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py

**Git log**:
!git log --oneline -10 2>/dev/null || echo "none"

**Git diff stat**:
!git diff HEAD --stat 2>/dev/null || echo "none"

**Today**:
!date +%Y-%m-%d

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

---

## Your role

You are capturing this session as a structured log entry and appending it to `session-log.md`. This is an append-only history file — never overwrite existing entries.

---

## Flow

**Step 1 — Read and draft**

Read the session activity (FILES_TOUCHED, CROSS_PROJECT_FILES, BASH_COMMANDS), git log, and git diff stat above. Draft a structured entry:

```
## YYYY-MM-DD
**Files changed:** [comma-separated relative paths, or "none"]
**Git:** [N commit(s) — "message of most recent"] or "none"
- [key action or decision]
- [key action or decision]
- [3–8 bullets total]
**Open threads:** [item] (omit section entirely if none)
```

**Step 2 — Confirm**

Show the draft. Ask: "Save to session-log.md? Reply `yes` or edit inline."

**Step 3 — Write**

On confirm: use the PATH shown in the **session-log.md** context above.

- If PATH file is MISSING: use Write tool to create it with header `# [Repo] Session Log\n\n` followed by the entry
- If PATH file exists: use Edit tool to append — match the final characters of the existing file content and append `\n\n` + the new entry

**Step 4 — Cross-project writes**

For each path in CROSS_PROJECT_FILES:
1. Determine the owning project: the path begins with PROJECT_DIR of a sibling repo. Match the path prefix against known sibling directories (use `~/.claude/projects/` keys or infer from the absolute path).
2. Derive the owning project's session-log.md path: `~/.claude/projects/[owner-key]/memory/session-log.md`
3. Append an attributed entry to that project's session-log.md:
   ```
   ## YYYY-MM-DD [← source-repo]
   **Cross-project work from [source-repo] session:**
   - [specific files/actions in this project]
   ```

---

## Constraints

- Append only — never overwrite existing session-log.md entries
- Use Edit tool for appending to existing files (match last few chars of file, append `\n\n` + entry)
- If FILES_TOUCHED is "none": note "No file changes detected" in the entry body, and ask the user to describe the session manually before saving
- One entry per run — do not batch multiple summaries
- Do not write to MEMORY.md — session history belongs in session-log.md only
