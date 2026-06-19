---
description: Use when the user wants to wrap up or end the session — "wrap", "I'm done", "close out", "end of session". Runs session log, git check, plan cleanup, backlog review, and done marker.
allowed-tools: Bash, Read, Write, Edit
# No model override: wrap runs at high context by design. A command-level model
# (e.g. claude-sonnet-4-6) resolves to the 200K-context variant and drops the
# session's 1M window — collapsing the %-used denominator and triggering an
# auto-compact loop. Inherit the session model so the window is preserved.
---

## Collect context

Run each command below now before proceeding. Store results mentally.

**Scope**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
```

**Session activity**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py
```

**Session log status**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py
```

**session-log.md** (full content, for skip check):
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
        print('SESSION_LOG: unavailable')
        exit(0)
log = projects_dir / key / 'memory' / 'session-log.md'
print(f'PATH: {log}')
print(log.read_text() if log.exists() else 'MISSING — will be created on first save')
"
```

**Git state, diff, unpushed commits, backlog, date**:
```bash
echo "GIT_DIFF_STAT:" && (git diff HEAD --stat 2>/dev/null || echo "none")
echo "GIT_STATE:" && (git status --short 2>/dev/null || echo "clean")
echo "UNPUSHED:" && (git log @{u}.. --oneline 2>/dev/null || echo "none (or no remote)")
REPO=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null)
DOMAIN=$(git rev-parse --show-toplevel 2>/dev/null | sed 's|.*/Repos/||' | cut -d'/' -f1)
TW_PROJECT="${DOMAIN}.${REPO}"
echo "IN_PROGRESS:" && (task rc.verbose=nothing project:${TW_PROJECT} +ACTIVE list 2>/dev/null || echo "(none)")
echo "UP_NEXT:" && (task rc.verbose=nothing project:${TW_PROJECT} limit:3 list 2>/dev/null || echo "(none)")
echo "DATE:" && date +%Y-%m-%d
```

**Plans**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py
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
    print(mem.read_text() if mem.exists() else 'MISSING')
elif mode == 'parent':
    print('PARENT MODE — see scope output for child projects')
else:
    import subprocess
    git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
    key = git_root.replace('/', '-')
    mem = projects_dir / key / 'memory' / 'MEMORY.md'
    print(f'PATH: {mem}')
    print(mem.read_text() if mem.exists() else 'MISSING')
"
```

---

## Your role

You are the end-of-session close-out assistant. Work through the steps below in order.
Each step is interactive — wait for the user's reply before proceeding to the next.
Do not skip steps unless the user says `skip`.

---

## Step 0 — Ramp

Invoke `/ramp:wrap` now using the Skill tool with no arguments. If the Skill tool returns an error or the skill is not found (ramp not installed), skip silently and proceed to Step 1. After ramp:wrap completes its full flow, continue with Step 1.

---

## Step 1 — Session log

Check the **session log** collected above. If SESSION_LOG already contains an entry whose header includes the first 8 chars of SESSION (from collect-summarize.py), pin was already run this session — skip to Step 2.

Otherwise, run the summarize flow using the session activity collected above:

1. Read FILES_TOUCHED, CROSS_PROJECT_FILES, BASH_COMMANDS, git log, and git diff stat
2. Draft a structured session-log entry:
   ```
   ## [date] · [first 8 chars of SESSION id from collect-summarize.py]
   **Files changed:** [comma-separated relative paths, or "none"]
   **Git:** [N commit(s) — "message of most recent"] or "none"
   - [key action or decision — 3–8 bullets]
   **What didn't work:** [failed approach — "tried X, failed because Y"] (omit if none)
   **Resume:** [exact next step to take when picking this up] (omit if nothing in flight)
   **Open threads:** [blocker or deferred item] (omit if none)
   ```
3. Show the draft. Ask: "Save to session-log.md? Reply `yes` or edit inline."
4. On confirm: append to `~/.claude/projects/[key]/memory/session-log.md`
   - If MISSING: create with Write tool using `# [Repo] Session Log\n\n` header
   - If exists: append with Edit tool (match last chars, append `\n\n` + entry)
5. Cross-project: for each path in CROSS_PROJECT_FILES, append an attributed entry to
   that project's session-log.md (infer owning project from the absolute path prefix):
   ```
   ## [date] · [8-char session id] [← source-repo]
   **Cross-project work from [source-repo] session:**
   - [specific files/actions in this project]
   ```

Constraints:
- Do NOT write to MEMORY.md — session history belongs in session-log.md only
- Append only — never overwrite existing entries

After saving the session log, run:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py | python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/update-project-map.py
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plan-map.py > /dev/null
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/post-save.py
```
First two commands refresh the project map and plan index.
`post-save.py` names the current session (if unnamed) and renames any other unnamed sessions in scope.
If output contains `Renamed:` lines, note them in your response.

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
- **Stale** — already has `_done-` prefix, or title suggests completed/abandoned work
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
mv ~/.claude/plans/[name].md ~/.claude/plans/_done-[name].md
```
Report: "Marked [N] plan(s) for deletion: [filenames]"

Never use `rm` — always rename with `_done-` prefix. Already-marked plans need no action.

---

## Step 4 — Backlog review

Read the **IN_PROGRESS** and **UP_NEXT** TaskWarrior output above.

If both are empty/nothing: say "Backlog: nothing in progress ✓" and move on.

Otherwise show the In Progress and Up Next items. Ask:
"Any items completed this session? Reply with task ID(s) or `skip`."

If IDs given: run `task ID done` for each confirmed item, then report completions.

---

## Step 5 — Memory health

Count the lines in the **Project MEMORY.md** content collected above (exclude the `PATH:` line).

- ≥ 150 lines: "⚠ MEMORY.md is [N] lines — approaching the 200-line truncation limit. Consider archiving older sections to a topic file before the next session."
- < 150 lines: "Memory: [N] lines ✓"
- MISSING: "Memory: not yet created ✓"

No user reply needed — informational only.

---

## Step 6 — Done marker

Ask: "Mark this session for deletion? Reply `yes` or `no`."

If `yes`, run:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/mark-session-done.py
```
Report the output — e.g., "Marked for deletion: [name]" or "Already marked: [name]".

If `no`: say "Session not marked for deletion." and proceed to wrap-up.

---

## Wrap-up

After all steps, show a one-line summary:
```
## Session closed — [date]
Session log: saved | Git: [clean/uncommitted] | Plans: [N deleted or "none"] | Backlog: [N completed or "none"] | Done: [marked/not marked]
```
