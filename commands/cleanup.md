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
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plugin-drift.py
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
