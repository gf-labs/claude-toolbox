---
description: End-of-session housekeeping — snapshot, git check, plan cleanup, backlog review, done marker
allowed-tools: Bash, Read, Write, Edit
---

## Auto-collected context

**Scope**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py

**Session activity**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py

**Git diff stat** (files changed):
!git diff HEAD --stat 2>/dev/null || echo "none"

**Git state**:
!git status --short 2>/dev/null || echo "clean"

**Unpushed commits**:
!git log @{u}.. --oneline 2>/dev/null || echo "none (or no remote)"

**Plans**:
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py

**Backlog (In Progress + Up Next)**:
!head -10 BACKLOG.md 2>/dev/null || echo "not found"

**Today**:
!date +%Y-%m-%d

---

## Your role

You are the end-of-session close-out assistant. Work through the steps below in order.
Each step is interactive — wait for the user's reply before proceeding to the next.
Do not skip steps unless the user says `skip`.

---

## Step 0 — Ramp check

Ask: "Did you run `/ramp:wrap` first? Reply `yes` or `skip` (skip if ramp is not installed)."

Wait for reply, then proceed to Step 1 regardless of answer.

---

## Step 1 — Session log

Run the summarize flow using the session activity collected above:

1. Read FILES_TOUCHED, CROSS_PROJECT_FILES, BASH_COMMANDS, git log, and git diff stat
2. Draft a structured session-log entry:
   ```
   ## [date]
   **Files changed:** [comma-separated relative paths, or "none"]
   **Git:** [N commit(s) — "message of most recent"] or "none"
   - [key action or decision — 3–8 bullets]
   **Open threads:** [item] (omit if none)
   ```
3. Show the draft. Ask: "Save to session-log.md? Reply `yes` or edit inline."
4. On confirm: append to `~/.claude/projects/[key]/memory/session-log.md`
   - If MISSING: create with Write tool using `# [Repo] Session Log\n\n` header
   - If exists: append with Edit tool (match last chars, append `\n\n` + entry)
5. Cross-project: for each path in CROSS_PROJECT_FILES, append an attributed entry to
   that project's session-log.md (infer owning project from the absolute path prefix):
   ```
   ## [date] [← source-repo]
   **Cross-project work from [source-repo] session:**
   - [specific files/actions in this project]
   ```

Constraints:
- Do NOT write to MEMORY.md — session history belongs in session-log.md only
- Append only — never overwrite existing entries

---

## Step 2 — Git check

Read the **Git state** and **Unpushed commits** collected above.

If git state is clean AND no unpushed commits: say "Git: clean ✓" and move on.

If uncommitted changes exist: list them and say:
"Uncommitted changes detected — address before closing? Reply `done` when ready or `skip`."
Wait for reply.

If unpushed commits exist: list them and say:
"Unpushed commits detected — push before closing? Reply `done` when ready or `skip`."
Wait for reply.

---

## Step 3 — Plan cleanup

Read the **Plans** output above.

If NONE: say "Plans: none ✓" and move on.

Otherwise, for each plan assess its relevance using the filename, title, and this session's FILES_TOUCHED:

- **This session** — plan was the focus of work done today (matches session activity)
- **Stale** — already has `-delete-me` in the name, or title suggests completed/abandoned work
- **Active** — appears in-progress or unrelated to this session

Present the assessment and your recommendation:
```
Plans — [N] found:

  keen-painting-pebble-delete-me.md  [stale — already marked]
  claude-toolbox-buildout.md         [active — keep]
  my-plan.md                         [this session → recommend: mark done]
```

If any plans are flagged "this session" or appear stale/completed but not yet marked:
Say: "Recommend marking done: [filename(s)]. Confirm? Reply `yes`, modify the list, or `skip`."

If all unmarked plans are active: say "Plans: [N] active, [N] already marked for cleanup ✓" and move on.

On confirmation, rename each recommended file:
```bash
mv ~/.claude/plans/[name].md ~/.claude/plans/[name]-delete-me.md
```
Report: "Marked [N] plan(s) for deletion: [filenames]"

Never use `rm` — always rename with `-delete-me` suffix. Already-marked plans need no action.

---

## Step 4 — Backlog review

Read the **Backlog** output above (In Progress + Up Next sections).

If both are empty/nothing: say "Backlog: nothing in progress ✓" and move on.

Otherwise show the In Progress and Up Next items. Ask:
"Any items completed this session? Reply with item name(s) or `skip`."

If items named: use Edit tool to mark them done in BACKLOG.md — move completed items
from `## In Progress` or `## Up Next` into a `## Done` section (create it if absent),
or remove them if the user prefers. Ask: "Move to Done section or remove entirely?"

---

## Step 5 — Memory health

Check MEMORY.md line count from the content collected above.

- ≥ 150 lines: "⚠ MEMORY.md is [N] lines — approaching the 200-line truncation limit. Consider archiving older sections to a topic file before the next session."
- < 150 lines: "Memory: [N] lines ✓"

No user reply needed — informational only.

---

## Step 6 — Done marker

Ask: "Mark this session for deletion? Reply `yes` or `no`."

If `yes`, run:
```bash
python3 -c "
import json, os
from pathlib import Path

cwd = os.getcwd()
proj_key = cwd.replace('/', '-')
proj_dir = Path.home() / '.claude' / 'projects' / proj_key

jsonl_files = list(proj_dir.glob('*.jsonl'))
if not jsonl_files:
    print('ERROR: No session files found in', proj_dir)
    exit(1)

current = max(jsonl_files, key=lambda f: f.stat().st_mtime)

last_title = ''
first_slug = ''
for line in current.read_text(errors='replace').splitlines():
    if not line.strip(): continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('type') == 'custom-title':
        last_title = obj.get('customTitle', '')
    if not first_slug and obj.get('slug'):
        first_slug = obj['slug']

base = last_title or first_slug or current.stem[:8]

if 'delete-me' in base:
    print(f'Already marked: {base}')
else:
    new_title = base + '-delete-me'
    record = json.dumps({'type': 'custom-title', 'customTitle': new_title, 'sessionId': current.stem})
    with open(current, 'a') as f:
        f.write(record + '\n')
    print(f'Marked for deletion: {new_title}')
"
```

---

## Wrap-up

After all steps, show a one-line summary:
```
## Session closed — [date]
Session log: saved | Git: [clean/uncommitted] | Plans: [N deleted or "none"] | Backlog: [N completed or "none"] | Done: [marked/not marked]
```
