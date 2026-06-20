---
description: Clean up old Claude session artifacts — extract context, then delete
argument-hint: [pattern] [--days N] [--dry-run]
allowed-tools: Bash, Read, Write, Edit
model: claude-sonnet-4-6
---

## Arguments

`$ARGUMENTS`

Parse from arguments:
- **Positional pattern** (any word not starting with `--`) — activates **Filter Mode** (see below). Matches against session title, first user message, and last-prompt content. Case-insensitive substring match.
- `--days N` — age threshold for OLD sessions (default: 30)
- `--dry-run` — run all phases and produce reports, but skip actual deletion

## Filter Mode

When a positional pattern is provided (e.g. `/cleanup "delete-me"` or `/cleanup 4794c719`), skip the normal scan phases and run this targeted flow instead.

**Step F1 — Find matching sessions:**

```bash
python3 -c "
import json, os, sys, shutil
from pathlib import Path

sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
try:
    from _scope import get_scope
    _m, _d, _ = get_scope()
    _allowed = {_d} if _m == 'single' else ({k for k, _ in _d} if _m == 'parent' else None)
except Exception:
    _allowed = None

pattern = 'PATTERN_PLACEHOLDER'.lower()
projects_dir = Path.home() / '.claude' / 'projects'
fh_dir = Path.home() / '.claude' / 'file-history'
debug_dir = Path.home() / '.claude' / 'debug'
senv_dir = Path.home() / '.claude' / 'session-env'

results = []

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    if _allowed is not None and proj.name not in _allowed: continue
    for f in sorted(proj.glob('*.jsonl')):
        try:
            custom_title = ''
            first_user = ''
            last_prompt = ''
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip(): continue
                obj = json.loads(line)
                t = obj.get('type', '')
                if t == 'custom-title':
                    custom_title = obj.get('customTitle', '')  # always take latest
                if t == 'last-prompt' and not last_prompt:
                    last_prompt = obj.get('lastPrompt', '')[:80]
                if t == 'user' and not first_user:
                    msg = obj.get('message', {})
                    if isinstance(msg, dict):
                        content = msg.get('content', '')
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get('type') == 'text':
                                    first_user = c.get('text', '')[:80]
                                    break
                        elif isinstance(content, str):
                            first_user = content[:80]
            searchable = (custom_title + ' ' + first_user + ' ' + last_prompt).lower()
            if pattern in searchable:
                sid = f.stem
                size_k = f.stat().st_size // 1024
                fh_path = fh_dir / sid
                fh_size = sum(ff.stat().st_size for ff in fh_path.rglob('*') if ff.is_file()) // 1024 if fh_path.exists() else 0
                dbg_path = debug_dir / (sid + '.txt')
                dbg_size = dbg_path.stat().st_size // 1024 if dbg_path.exists() else 0
                senv_path = senv_dir / sid
                senv_size = sum(ff.stat().st_size for ff in senv_path.rglob('*') if ff.is_file()) // 1024 if senv_path.exists() else 0
                proj_dir = proj / sid
                dir_size = sum(ff.stat().st_size for ff in proj_dir.rglob('*') if ff.is_file()) // 1024 if proj_dir.exists() else 0
                total_k = size_k + fh_size + dbg_size + senv_size + dir_size
                print(f'MATCH|{proj.name}|{sid}|{size_k}K|{fh_size}K|{dbg_size}K|{senv_size}K|{dir_size}K|{total_k}K|{custom_title or first_user[:50]!r}')
        except Exception as e:
            pass
"
```

Replace `PATTERN_PLACEHOLDER` with the actual pattern from `$ARGUMENTS`.

**Step F2 — Present for review:**

Show the user a single consolidated table — one row per file, grouped by session. Include full paths. Omit columns/rows for file types that don't exist for any matched session.

```
### Sessions matching "[pattern]" — [N] session(s) · [total]K

| Session | Title | Type | Path | Size |
|---------|-------|------|------|------|
| 4794c719 | bug-report-test-delete-me | JSONL        | ~/.claude/projects/[proj]/[uuid].jsonl    | 358K |
| 4794c719 |                           | file-history | ~/.claude/file-history/[uuid]/            | 26K  |
| 4794c719 |                           | debug        | ~/.claude/debug/[uuid].txt               | 215K |
| 4794c719 |                           | session-env  | ~/.claude/session-env/[uuid]/             | 0K   |
| a5734a17 | bug-report-test-alt-...   | JSONL        | ~/.claude/projects/[proj]/[uuid].jsonl    | 10K  |
| a5734a17 |                           | file-history | ~/.claude/file-history/[uuid]/            | 278K |
| a5734a17 |                           | debug        | ~/.claude/debug/[uuid].txt               | 31K  |
```

Rules:
- Repeat Session and Title only on the first row for each session; leave blank for subsequent rows of the same session
- If a file type doesn't exist for a session, omit that row (don't show it with empty path)
- Use `~` shorthand for `$HOME` in paths for readability

Reply `yes` to delete all of the above, or `no` to cancel.

If no matches found: say "No sessions found matching '[pattern]'." and stop.

**Step F3 — Delete on confirmation:**

If user replies `yes`:
```bash
PROJ="$HOME/.claude/projects"
FH="$HOME/.claude/file-history"
DBG="$HOME/.claude/debug"
SENV="$HOME/.claude/session-env"
rm -f "$PROJ/[proj]/[session-id].jsonl"
rm -rf "$PROJ/[proj]/[session-id]/"
rm -rf "$FH/[session-id]/"
rm -f "$DBG/[session-id].txt"
rm -rf "$SENV/[session-id]/"
```
Repeat for each matched session. Then report: "Deleted [N] session(s) · [size] freed."

If `--dry-run` is in arguments: show the table and report "DRY RUN — no files deleted."

---

## Step 0 — Collect context

Run each Bash command below now before proceeding. Store the output mentally — it is the input for all phases.

**Scope** (single project, parent roll-up, or global):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
```

**Session inventory** (age, size, OLD/KEEP/ARTIFACT/DELETE-ME status — registry-aware):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-sessions.py $ARGUMENTS
```

**Session directories** (tool-results, subagents — OLD sessions only):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-dirs.py $ARGUMENTS
```

**File-history by session**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-file-history.py $ARGUMENTS
```

**Debug logs by session**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-debug.py $ARGUMENTS
```

**Memory health per project**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-memory.py
```

**Plans inventory**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py
```

**Orphaned project keys** (source dir no longer exists on disk):
```bash
python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from pathlib import Path
from _scope import _reconstruct
projects_dir = Path.home() / '.claude' / 'projects'
found = []
for d in sorted(projects_dir.iterdir()):
    if not d.is_dir(): continue
    if not list(_reconstruct(d.name, None)):
        sessions = sum(1 for _ in d.glob('*.jsonl'))
        size_k = sum(f.stat().st_size for f in d.rglob('*') if f.is_file()) // 1024
        found.append(f'{d.name}\t{sessions} sessions\t{size_k}K')
print('\n'.join(found) if found else 'NONE')
"
```

**Session-env dirs** (per-session environment snapshots):
```bash
python3 -c "
from pathlib import Path
d = Path.home() / '.claude' / 'session-env'
if not d.exists():
    print('NONE')
else:
    empty = sum(1 for x in d.iterdir() if x.is_dir() and not any(x.iterdir()))
    nonempty = [(x.name, sum(f.stat().st_size for f in x.rglob('*') if f.is_file())//1024)
                for x in sorted(d.iterdir()) if x.is_dir() and any(x.iterdir())]
    print(f'EMPTY_COUNT\t{empty}')
    for name, size in nonempty:
        print(f'NONEMPTY\t{name}\t{size}K')
"
```

**Reference docs** (durable context artifacts):
```bash
ls ~/.claude/docs/ 2>/dev/null || echo "NONE"
```

**Disk usage**:
```bash
du -sh ~/.claude/projects/ ~/.claude/file-history/ ~/.claude/debug/ ~/.claude/session-env/ 2>/dev/null
```

**Plugin cache** (marketplace cache vs active plugins):
```bash
python3 -c "
import json
from pathlib import Path
cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
settings = json.loads((Path.home() / '.claude' / 'settings.json').read_text())
installed_file = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'
installed = json.loads(installed_file.read_text()).get('plugins', {}) if installed_file.exists() else {}
enabled = settings.get('enabledPlugins', {})
cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) // (1024*1024) if cache_dir.exists() else 0
cache_dirs = [d.name for d in cache_dir.iterdir() if d.is_dir()] if cache_dir.exists() else []
print(f'CACHE_MB={cache_size}')
print(f'CACHE_DIRS={cache_dirs}')
print(f'ENABLED={list(enabled.keys())}')
print(f'INSTALLED={list(installed.keys())}')
"
```

**Plugin cache drift** (cached commands vs source repo):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plugin-drift.py
```

---

## Your role

You are a Claude artifact cleanup assistant. Run all commands in Step 0 first, then work through the phases below using that output.

Respect the `--days N` argument if provided — use that number instead of 30 for the age threshold. Adjust the OLD/KEEP labels accordingly by recalculating from session ages shown above.

If `--dry-run` is in the arguments: run all phases, produce all reports, but skip the actual deletion in Phases 1, 2, and 3. Say "DRY RUN — no files deleted" at the end.

---

## Phase 0 — Plugin data policy scan

Scan `~/.claude/data/*/data-policy.json` and display what each plugin owns:

```bash
python3 -c "
import json
from pathlib import Path
data_root = Path.home() / '.claude' / 'data'
if not data_root.exists():
    print('No plugin data found.')
else:
    found = False
    for policy_file in sorted(data_root.glob('*/data-policy.json')):
        plugin = policy_file.parent.name
        try:
            policy = json.loads(policy_file.read_text())
            for d in policy.get('dirs', []):
                full = policy_file.parent / d['path']
                if full.is_dir():
                    count = sum(1 for _ in full.rglob('*') if _.is_file())
                    size = f'{count} files'
                elif full.is_file():
                    size = '1 file'
                else:
                    size = 'empty'
                print(f'  {plugin}/{d[\"path\"]}  [{d[\"cleanup\"]}]  {size}')
                found = True
        except Exception as e:
            print(f'  {plugin}: error reading policy — {e}')
    if not found:
        print('No plugin data found.')
"
```

Display the summary. No user action needed — informational only. Proceed to Phase 1.

Also surface hygiene issues from Step 0:

**MEMORY.md size:**
- For any project showing `WARN:NEAR-LIMIT` (≥150 lines): say "⚠ [project] MEMORY.md is [N] lines — approaching 200-line truncation limit. Consider archiving older sessions to a topic file."
- Truncation silently drops the bottom of the file on load — the most recently added content is cut off first.

**Orphaned project keys:**
- If the Orphaned project keys output from Step 0 is not `NONE`, list them with session counts and sizes
- These are project dirs whose source repo was moved, renamed, or deleted — the key no longer maps to any real path on disk
- Say: "Found [N] orphaned project key dir(s) — will be handled in Phase 4."

**Session-env:**
- Report the empty count from the Session-env output
- If empty count > 0: "Found [N] empty session-env dirs — will be auto-deleted in Phase 1."
- List any NONEMPTY dirs with their sizes

**Reference docs:**
- List what's in `~/.claude/docs/` if anything exists
- If NONE: remind "No reference docs found. Consider storing stable background context (motivation docs, JDs, architecture decisions) as `.md` files in `~/.claude/docs/` so they survive context compaction."

---

## Phase 1 — Artifact deletion

Sessions with status `ARTIFACT` (from registry or detected via JSONL scan) are deleted automatically without prompting. The `collect-sessions.py` output from Step 0 provides registry-aware status — prefer registry status as the primary source; fall back to JSONL scanning for unregistered sessions.

Use the scope output from Step 0 to label the report:
- **Single mode** (`SINGLE [name] (key)`): label is the project name
- **Parent mode** (`PARENT [path] — N projects: [...]`): label is the parent path and project count
- **Global mode** (`GLOBAL`): label is "all projects"

In **parent mode**, lead with a grouped summary table before the per-session details:

```
## Claude Cleanup — [date] — [parent-path] ([N] projects)

### Projects summary

| Project | Old sessions | Artifact files | Size |
|---------|-------------|---------------|------|
| claude-toolbox | 3 | 1 | 450K |
| ramp | 1 | 0 | 120K |
| gfl-marketplace | 0 | 0 | — |
```

In **single** or **global** mode, use the standard format below.

Present a clean summary:

```
## Claude Cleanup — [date] — [scope label]

### Artifact-only files (safe to delete immediately — not real sessions)

| Project | File | Age | Size | Type |
|---------|------|-----|------|------|
| ...     | ...  | ...d | ...K | file-history-snapshot |

Note: These are internal Claude Code artifacts (e.g. file-history snapshots) that appear
as unnamed sessions in /resume but contain no conversation content. Always delete these.
```

**Auto-delete artifact-only files and empty session-env dirs (no confirmation needed):**

Delete immediately without asking:
1. ARTIFACT-status JSONL files (contain no conversation content — from registry or JSONL detection)
2. Empty session-env dirs (all reported in Step 0)
3. session-env dirs belonging to ARTIFACT sessions

Use full absolute paths — never relative paths starting with `-`, which `rm` interprets as flags:
```bash
PROJ="$HOME/.claude/projects"
rm -f "$PROJ/[proj]/[session-id].jsonl"  # repeat for each ARTIFACT entry
rm -rf "$HOME/.claude/session-env/[session-id]/"  # session-env for each ARTIFACT
```

Delete all empty session-env dirs in one pass:
```bash
python3 -c "
import shutil
from pathlib import Path
d = Path.home() / '.claude' / 'session-env'
deleted = 0
for x in sorted(d.iterdir()):
    if x.is_dir() and not any(x.iterdir()):
        x.rmdir()
        deleted += 1
print(f'Deleted {deleted} empty session-env dirs')
"
```

Report: "Auto-deleted [N] artifact file(s) · [M] empty session-env dirs"

Also show the memory health table:
```
### Memory health
| Project | MEMORY.md | Status |
|---------|-----------|--------|
| ...     | N lines   | OK / THIN / MISSING |
```

---

## Phase 2 — Done session deletion

Sessions with status `DELETE-ME` (from registry `done` status or `delete-me` in custom-title) are offered for deletion. Sessions with status `KEEP` (from registry `keep` status) are listed but skipped — never offered for deletion.

The `collect-sessions.py` output from Step 0 is the primary source for session status. Registry status takes precedence over JSONL-detected status for registered sessions; unregistered sessions fall back to JSONL scanning.

Present what will be removed and ask for confirmation:

```
### Sessions to remove (>[N] days old, registry `done`, or marked delete-me)

| Project | Session | Age | Size | Reason |
|---------|---------|-----|------|--------|
| ...     | ...     | ...d | ...K | old / done / delete-me |

### Sessions kept (registry `keep` — skipped)

| Project | Session | Age | Size |
|---------|---------|-----|------|
| ...     | ...     | ...d | ...K |

Total pending deletion: X sessions · Y MB (including session dirs, file-history, debug logs, session-env)

Proceed? Reply `yes` to delete, anything else to cancel.
```

After presenting the Phase 2 report, say: "To preview a session's content before deciding, reply `preview [session-id]`."

If user replies `preview [session-id]`:
1. Find and read the JSONL at `~/.claude/projects/[proj]/[session-id].jsonl`
2. Parse: `custom-title`, first user message, tool_use blocks (files written/edited, bash commands, git commits), any `summary` entries
3. Output a one-screen summary:
   ```
   ## Session: [first 8 chars] — [title or "(untitled)"]
   **Date**: [mtime date]  **Size**: [K]

   **What happened** (3–6 bullets):
   - [key action or decision]

   **Files changed**: [comma-separated, or "none detected"]
   **Commits**: [N — "most recent subject", or "none"]
   ```
4. Re-prompt: "Delete this session, skip it, or preview another? Reply `delete [id]`, `skip`, or `preview [id]`."

**If user confirms `yes`:** Use Bash to delete each listed path:
```bash
PROJ="$HOME/.claude/projects"
FH="$HOME/.claude/file-history"
DBG="$HOME/.claude/debug"
SENV="$HOME/.claude/session-env"
rm -f "$PROJ/[proj]/[session-id].jsonl"
rm -rf "$PROJ/[proj]/[session-id]/"
rm -rf "$FH/[session-id]/"
rm -f "$DBG/[session-id].txt"
rm -rf "$SENV/[session-id]/"
```

After deletion, run `du -sh ~/.claude/projects/ ~/.claude/file-history/ ~/.claude/debug/ ~/.claude/session-env/` and show the new totals.

**Never delete:**
- `~/.claude/history.jsonl`
- `~/.claude.json` or `~/.claude/settings.json`
- `~/.claude/CLAUDE.md`
- `~/.claude/projects/*/memory/MEMORY.md`
- `~/.claude/projects/*/memory/session-log.md`
- Any session newer than the threshold
- The current active session (most recent `.jsonl` per project)
- Any session with registry status `KEEP`

---

## Phase 3 — Plan archival

Move completed plans (those with `_done-` prefix) from `~/.claude/plans/` to `~/.claude/plans/archive/`:

```bash
python3 -c "
import shutil
from pathlib import Path
plans_dir = Path.home() / '.claude' / 'plans'
archive_dir = plans_dir / 'archive'
if not plans_dir.exists():
    print('No plans directory.')
else:
    archive_dir.mkdir(exist_ok=True)
    moved = []
    for f in sorted(plans_dir.glob('_done-*.md')):
        dest = archive_dir / f.name
        shutil.move(str(f), str(dest))
        moved.append(f.name)
    if moved:
        print(f'Archived {len(moved)} plan(s):')
        for name in moved:
            print(f'  {name}')
    else:
        print('No completed plans to archive.')
"
```

No user confirmation needed. Report the count.

---

## Phase 4 — Orphaned project keys

If the **Orphaned project keys** output from Step 0 showed any entries (not `NONE`), handle them here.

These are project dirs whose source repository was moved, renamed, or deleted — the key no longer maps to any real path on disk. They accumulate over time as repos are reorganized.

Show a summary table:
```
### Orphaned project key directories (source dir gone)

| Directory | Sessions | Size |
|-----------|----------|------|
| -Users-you-Repos-old-project | 3 | 1200K |
| ...                                  | ...| ...  |

Total: N directories · X MB
```

Warn for any directory with sessions > 0: "⚠ [name] has [N] sessions — context will be lost. Confirm deletion."

Ask: "Delete all orphaned project key directories? Reply `yes` to delete, anything else to cancel."

**If user confirms `yes`:**
```bash
python3 -c "
import sys, os, shutil
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from pathlib import Path
from _scope import _reconstruct
projects_dir = Path.home() / '.claude' / 'projects'
deleted = []
for d in sorted(projects_dir.iterdir()):
    if d.is_dir() and not list(_reconstruct(d.name, None)):
        shutil.rmtree(d)
        deleted.append(d.name)
print('Deleted:', deleted)
"
```

Report: "Deleted [N] orphaned project key directories."

If `--dry-run`: show the table and report "DRY RUN — no directories deleted."

Also handle plugin cache cleanup (auto, no confirmation):

Check if the plugin cache is orphaned:
```bash
python3 -c "
import json
from pathlib import Path
cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
settings = json.loads((Path.home() / '.claude' / 'settings.json').read_text())
installed_file = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'
installed = json.loads(installed_file.read_text()).get('plugins', {}) if installed_file.exists() else {}
enabled = settings.get('enabledPlugins', {})
cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) // (1024*1024) if cache_dir.exists() else 0
cache_dirs = [d.name for d in cache_dir.iterdir() if d.is_dir()] if cache_dir.exists() else []
print(f'CACHE_MB={cache_size}')
print(f'CACHE_DIRS={cache_dirs}')
print(f'ENABLED={list(enabled.keys())}')
print(f'INSTALLED={list(installed.keys())}')
"
```

**Orphaned** = cache is non-empty AND both `enabledPlugins` and `installed_plugins` are empty.

If orphaned: delete automatically (cache is fully reconstructable via `/plugin install`):
```bash
python3 -c "
import shutil
from pathlib import Path
cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
deleted = []
for d in sorted(cache_dir.iterdir()):
    if d.is_dir():
        size_mb = sum(f.stat().st_size for f in d.rglob('*') if f.is_file()) // (1024*1024)
        shutil.rmtree(d)
        deleted.append(f'{d.name} ({size_mb}MB)')
print('Deleted:', deleted)
"
```

Report: "Auto-deleted orphaned plugin cache: [names] · [total]MB freed."

If not orphaned (plugins active or cache empty): skip silently.

If `--dry-run`: report "DRY RUN — orphaned plugin cache would be deleted: [N]MB."

---

## Phase 5 — Manual plugin data review

For each directory marked `cleanup: manual` in the Phase 0 scan, show it and ask if the user wants to review:

```bash
python3 -c "
import json
from pathlib import Path
data_root = Path.home() / '.claude' / 'data'
if data_root.exists():
    for policy_file in sorted(data_root.glob('*/data-policy.json')):
        plugin = policy_file.parent.name
        try:
            policy = json.loads(policy_file.read_text())
            for d in policy.get('dirs', []):
                if d.get('cleanup') == 'manual':
                    full = policy_file.parent / d['path']
                    if full.is_dir():
                        count = sum(1 for _ in full.rglob('*') if _.is_file())
                        print(f'MANUAL: {plugin}/{d[\"path\"]}  {count} files  ({full})')
        except Exception:
            pass
"
```

For each `MANUAL:` line, ask: "Review `<path>`? Reply `yes` or `skip`." If yes, list the files. No automated action — user decides.

---

## Summary

```
## Done

Removed: X sessions · Y MB freed
Plans archived: [N] or "none"
Skipped: [list of projects kept, if any]
```
