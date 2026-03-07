---
description: Clean up old Claude session artifacts — extract context, then delete
argument-hint: [pattern] [--days N] [--dry-run]
allowed-tools: Bash, Read, Write, Edit
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
import json, shutil
from pathlib import Path

pattern = 'PATTERN_PLACEHOLDER'.lower()
projects_dir = Path.home() / '.claude' / 'projects'
fh_dir = Path.home() / '.claude' / 'file-history'
debug_dir = Path.home() / '.claude' / 'debug'

results = []

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    for f in sorted(proj.glob('*.jsonl')):
        try:
            custom_title = ''
            first_user = ''
            last_prompt = ''
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip(): continue
                obj = json.loads(line)
                t = obj.get('type', '')
                if t == 'custom-title' and not custom_title:
                    custom_title = obj.get('customTitle', '')
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
                proj_dir = proj / sid
                dir_size = sum(ff.stat().st_size for ff in proj_dir.rglob('*') if ff.is_file()) // 1024 if proj_dir.exists() else 0
                total_k = size_k + fh_size + dbg_size + dir_size
                print(f'MATCH|{proj.name}|{sid}|{size_k}K|{fh_size}K|{dbg_size}K|{dir_size}K|{total_k}K|{custom_title or first_user[:50]!r}')
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
rm -f "$PROJ/[proj]/[session-id].jsonl"
rm -rf "$PROJ/[proj]/[session-id]/"
rm -rf "$FH/[session-id]/"
rm -f "$DBG/[session-id].txt"
```
Repeat for each matched session. Then report: "Deleted [N] session(s) · [size] freed."

If `--dry-run` is in arguments: show the table and report "DRY RUN — no files deleted."

---

## Step 0 — Collect context

Run each Bash command below now before proceeding. Store the output mentally — it is the input for all phases.

**Session inventory** (age, size, OLD/KEEP/ARTIFACT status):
```bash
python3 -c "
import json, os, time
from pathlib import Path

claude_dir = Path.home() / '.claude'
projects_dir = claude_dir / 'projects'
cutoff_days = 30
cutoff = time.time() - cutoff_days * 86400

ARTIFACT_TYPES = {'file-history-snapshot'}
CONVERSATION_TYPES = {'user', 'assistant', 'progress', 'system', 'custom-title', 'last-prompt', 'queue-operation', 'summary'}

def is_artifact_only(path):
    try:
        for line in path.read_text().splitlines():
            obj = json.loads(line)
            t = obj.get('type', '')
            if t in CONVERSATION_TYPES:
                return False
            if t not in ARTIFACT_TYPES:
                return False  # unknown type — treat as conversation to be safe
        return True
    except Exception:
        return False

if not projects_dir.exists():
    print('NO PROJECTS DIR')
else:
    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir():
            continue
        for f in sorted(proj.iterdir()):
            if not f.name.endswith('.jsonl'):
                continue
            try:
                stat = f.stat()
                age = (time.time() - stat.st_mtime) / 86400
                custom_title = ''
                try:
                    for line in f.read_text(errors='replace').splitlines():
                        obj2 = json.loads(line)
                        if obj2.get('type') == 'custom-title':
                            custom_title = obj2.get('customTitle', '')
                            break
                except Exception:
                    pass
                if is_artifact_only(f):
                    status = 'ARTIFACT'
                else:
                    status = 'OLD' if stat.st_mtime < cutoff else 'KEEP'
                label = f'  title={custom_title!r}' if custom_title else ''
                print(f'{proj.name}  {f.stem}  {age:.0f}d  {stat.st_size // 1024}K  {status}{label}')
            except Exception as e:
                print(f'ERROR: {f} — {e}')
"
```

**Session directories** (tool-results, subagents — OLD sessions only):
```bash
python3 -c "
import os, time
from pathlib import Path

projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - 30 * 86400

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
        continue
    for entry in sorted(proj.iterdir()):
        if not entry.is_dir() or entry.name == 'memory':
            continue
        jsonl = proj / (entry.name + '.jsonl')
        if jsonl.exists() and jsonl.stat().st_mtime < cutoff:
            size = sum(f.stat().st_size for f in entry.rglob('*') if f.is_file())
            print(f'{proj.name}  {entry.name}/  {size // 1024}K  OLD-DIR')
" 2>/dev/null || echo "none"
```

**File-history by session**:
```bash
python3 -c "
import os, time
from pathlib import Path

fh_dir = Path.home() / '.claude' / 'file-history'
projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - 30 * 86400

if not fh_dir.exists():
    print('NONE')
else:
    old_sessions = set()
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        for f in proj.iterdir():
            if f.name.endswith('.jsonl') and f.stat().st_mtime < cutoff:
                old_sessions.add(f.stem)
    for session_dir in sorted(fh_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        if session_dir.name in old_sessions:
            size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
            print(f'file-history/{session_dir.name}  {size // 1024}K  OLD')
" 2>/dev/null || echo "none"
```

**Debug logs by session**:
```bash
python3 -c "
import os, time
from pathlib import Path

debug_dir = Path.home() / '.claude' / 'debug'
projects_dir = Path.home() / '.claude' / 'projects'
cutoff = time.time() - 30 * 86400

if not debug_dir.exists():
    print('NONE')
else:
    old_sessions = set()
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        for f in proj.iterdir():
            if f.name.endswith('.jsonl') and f.stat().st_mtime < cutoff:
                old_sessions.add(f.stem)
    for f in sorted(debug_dir.iterdir()):
        if f.stem in old_sessions:
            print(f'debug/{f.name}  {f.stat().st_size // 1024}K  OLD')
" 2>/dev/null || echo "none"
```

**Memory health per project**:
```bash
python3 -c "
from pathlib import Path

projects_dir = Path.home() / '.claude' / 'projects'
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir():
        continue
    mem = proj / 'memory' / 'MEMORY.md'
    if mem.exists():
        lines = len(mem.read_text().splitlines())
        status = 'THIN' if lines < 50 else 'OK'
        print(f'{proj.name}  {lines} lines  {status}')
    else:
        print(f'{proj.name}  NO MEMORY.md  MISSING')
"
```

**Plans inventory**:
```bash
python3 -c "
from pathlib import Path
plans_dir = Path.home() / '.claude' / 'plans'
if not plans_dir.exists() or not list(plans_dir.glob('*.md')):
    print('NONE')
else:
    for f in sorted(plans_dir.glob('*.md')):
        lines = len(f.read_text().splitlines())
        title = ''
        for line in f.read_text().splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                break
        print(f'{f.name}  {lines}L  {title[:60]}')
" 2>/dev/null || echo "check failed"
```

**MEMORY.md size check** (truncation risk at 200 lines):
```bash
python3 -c "
from pathlib import Path
projects_dir = Path.home() / '.claude' / 'projects'
for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    mem = proj / 'memory' / 'MEMORY.md'
    if mem.exists():
        lines = len(mem.read_text().splitlines())
        warn = 'WARN:NEAR-LIMIT' if lines >= 150 else ('OK' if lines >= 30 else 'THIN')
        print(f'{proj.name}  {lines}L  {warn}')
" 2>/dev/null || echo "check failed"
```

**Reference docs** (durable context artifacts):
```bash
ls ~/.claude/docs/ 2>/dev/null || echo "NONE"
```

**Disk usage**:
```bash
du -sh ~/.claude/projects/ ~/.claude/file-history/ ~/.claude/debug/ 2>/dev/null
```

**Plugin cache drift** (cached commands vs source repo):
```bash
python3 -c "
import json, os
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
cache_base = Path.home() / '.claude' / 'plugins' / 'cache'

try:
    settings = json.loads(settings_path.read_text())
except Exception:
    print('SETTINGS_UNREADABLE')
    exit()

marketplaces = settings.get('extraKnownMarketplaces', {})
enabled = settings.get('enabledPlugins', {})

if not enabled:
    print('NO_PLUGINS_ENABLED')
    exit()

for plugin_at_market in [k for k, v in enabled.items() if v]:
    parts = plugin_at_market.split('@', 1)
    if len(parts) != 2:
        continue
    plugin_name, market_name = parts
    market_entry = marketplaces.get(market_name)
    if not market_entry:
        print(f'{plugin_at_market}: marketplace source path unknown')
        continue
    source_dir = market_entry.get('source', {}).get('path') if isinstance(market_entry, dict) else None
    if not source_dir:
        print(f'{plugin_at_market}: marketplace source path not resolvable')
        continue
    source_commands = set(
        f.stem for f in (Path(source_dir) / 'commands').glob('*.md')
    ) if (Path(source_dir) / 'commands').exists() else set()
    cache_plugin = cache_base / market_name / plugin_name
    cached_versions = sorted(cache_plugin.iterdir()) if cache_plugin.exists() else []
    if not cached_versions:
        print(f'{plugin_at_market}: NO CACHE FOUND')
        continue
    latest = cached_versions[-1]
    cached_commands = set(
        f.stem for f in (latest / 'commands').glob('*.md')
    ) if (latest / 'commands').exists() else set()
    stale = cached_commands - source_commands
    missing = source_commands - cached_commands
    if stale or missing:
        print(f'{plugin_at_market} (cache: {latest.name}):')
        for c in sorted(stale):   print(f'  STALE  {c} — in cache but not in source')
        for c in sorted(missing): print(f'  MISSING {c} — in source but not in cache')
        print(f'  Fix: /plugin marketplace add {source_dir} then /plugin install {plugin_at_market}')
    else:
        print(f'{plugin_at_market}: cache in sync ({len(cached_commands)} commands)')
" 2>/dev/null || echo "check failed"
```

---

## Your role

You are a Claude artifact cleanup assistant. Run all commands in Step 0 first, then work through the phases below using that output.

Respect the `--days N` argument if provided — use that number instead of 30 for the age threshold. Adjust the OLD/KEEP labels accordingly by recalculating from session ages shown above.

If `--dry-run` is in the arguments: run all phases, produce all reports, but skip the actual deletion in Phase 3. Say "DRY RUN — no files deleted" at the end.

---

## Phase 0 — Hygiene report

Before touching sessions, surface structural issues:

**Plans:**
- List all plans from the Plans inventory above: name, line count, title
- Flag any that appear completed (title starts with "Plan:" and the work is likely done based on title)
- Prompt: "Found [N] plan(s). Review each and reply `delete [name]` to remove, or `keep` to skip."

**MEMORY.md size:**
- For any project showing `WARN:NEAR-LIMIT` (≥150 lines): say "⚠ [project] MEMORY.md is [N] lines — approaching 200-line truncation limit. Consider archiving older sessions to a topic file."
- Truncation silently drops the bottom of the file on load — the most recently added content is cut off first.

**Reference docs:**
- List what's in `~/.claude/docs/` if anything exists
- If NONE: remind "No reference docs found. Consider storing stable background context (motivation docs, JDs, architecture decisions) as `.md` files in `~/.claude/docs/` so they survive context compaction."

---

## Phase 1 — Scan report

Present a clean summary:

```
## Claude Cleanup — [date]

### Artifact-only files (safe to delete immediately — not real sessions)

| Project | File | Age | Size | Type |
|---------|------|-----|------|------|
| ...     | ...  | ...d | ...K | file-history-snapshot |

Note: These are internal Claude Code artifacts (e.g. file-history snapshots) that appear
as unnamed sessions in /resume but contain no conversation content. Always delete these.

### Sessions to remove (>[N] days old)

| Project | Session | Age | Size |
|---------|---------|-----|------|
| ...     | ...     | ...d | ...K |

Total: X sessions · Y MB (including session dirs, file-history, debug logs)

### Memory health
| Project | MEMORY.md | Status |
|---------|-----------|--------|
| ...     | N lines   | OK / THIN / MISSING |
```

---

## Phase 2 — Context extraction

For any project where:
- Old sessions exist **AND**
- MEMORY.md is THIN (<50 lines) or MISSING

Offer to extract context before deleting. Say:

> "**[project-name]** has old sessions but thin/missing memory ([N] lines). Extract key context before deleting? Reply `extract [project-name]` or `skip`."

If user says `extract [project]`:
1. Use the Read tool to read the old session `.jsonl` files for that project at `~/.claude/projects/[project-dir]/[session-id].jsonl`
2. From the JSONL, extract only the `display` fields (user prompts) — these are the lightest representation of what was discussed
3. Identify: key decisions made, architectural patterns established, bugs fixed, recurring patterns
4. Append a dated section to `~/.claude/projects/[project-dir]/memory/MEMORY.md` (create it if missing):
   ```
   ## Extracted from old sessions — [date]
   [concise bullet points of key context]
   ```
5. Confirm: "Extracted [N] key items from [session-count] sessions into MEMORY.md."

If user says `skip` or project has adequate memory: proceed to Phase 3.

---

## Phase 3 — Delete

**Step 3a — Auto-delete artifact-only files (no confirmation needed):**

ARTIFACT-status files contain no conversation content and are always safe to remove. Delete them immediately without asking.

Use full absolute paths — never relative paths starting with `-`, which `rm` interprets as flags:
```bash
PROJ="$HOME/.claude/projects"
rm -f "$PROJ/[proj]/[session-id].jsonl"  # repeat for each ARTIFACT entry
```
Report: "Auto-deleted [N] artifact file(s): [filenames]"

**Step 3b — Delete old sessions (requires confirmation):**

Show exactly what will be removed, then ask for confirmation:

```
### Ready to delete

- ~/.claude/projects/[proj]/[session-id].jsonl  ([size])
- ~/.claude/projects/[proj]/[session-id]/       ([size], tool-results + subagents)
- ~/.claude/file-history/[session-id]/          ([size])
- ~/.claude/debug/[session-id].txt              ([size])
...

Total: X files · Y MB

Proceed? Reply `yes` to delete, anything else to cancel.
```

**If user confirms `yes`:** Use Bash to delete each listed path:
```bash
rm -f ~/.claude/projects/[proj]/[session-id].jsonl
rm -rf ~/.claude/projects/[proj]/[session-id]/
rm -rf ~/.claude/file-history/[session-id]/
rm -f ~/.claude/debug/[session-id].txt
```

After deletion, run `du -sh ~/.claude/projects/ ~/.claude/file-history/ ~/.claude/debug/` and show the new totals.

**Never delete:**
- `~/.claude/history.jsonl`
- `~/.claude.json` or `~/.claude/settings.json`
- `~/.claude/CLAUDE.md`
- `~/.claude/projects/*/memory/MEMORY.md`
- Any session newer than the threshold
- The current active session (most recent `.jsonl` per project)

---

## Phase 4 — Summary

```
## Done

Removed: X sessions · Y MB freed
Memory extracted: [list of projects] or "none"
Skipped: [list of projects kept, if any]
```
