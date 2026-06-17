---
description: Break checkpoint — status display, session log, optional MEMORY.md update
allowed-tools: Bash, Read, Write, Edit
# No model override: pin runs at high context by design. A command-level model
# (e.g. claude-sonnet-4-6) resolves to the 200K-context variant and drops the
# session's 1M window — collapsing the %-used denominator and triggering an
# auto-compact loop. Inherit the session model so the window is preserved.
---

## Collect context

Run this **once** — it derives scope once, reads the session JSONL once, and emits
every section pin needs in a single pass:

```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-pin.py
```

Output is delimited by `=== SECTION ===` markers. Read the values from each:

| Section | Fields |
|---------|--------|
| `SCOPE` | `MODE`, `PROJECT_KEY`, `PROJECT_DIR`, `REPO`, `TW_PROJECT`, `DATE` |
| `SESSION` | `SESSION` (id), `TITLE`, `FILES_TOUCHED`, `CROSS_PROJECT_FILES`, `BASH_COMMANDS` |
| `GIT` | `BRANCH`, `CHANGES`, `GIT_LOG`, `GIT_DIFF_STAT` |
| `BACKLOG` | `IN_PROGRESS`, `UP_NEXT` (TaskWarrior) |
| `STATUS` | `LAST_SNAPSHOT`, `SESSIONS_SINCE`, `LAST_SESSION_LOG`, `LOG_ENTRIES` |
| `SESSION_LOG` | `PATH`, `REPEAT_PIN` (+ next header suffix), `LAST_ENTRY`, `SAME_SESSION_ENTRIES` |
| `MEMORY` | `PATH`, `LINES`, `MIGRATION` / `MIGRATION_NEEDED`, `CONTENT` (full) or `TAIL` (only if very large) |
| `PLANS` | plan inventory (or `NONE`) |
| `PLUGIN_DRIFT` | plugin cache drift (or `unavailable`) |
| `RAMP` | nodes due / level / XP (or `RAMP: no graph`) |

Notes:
- `SESSION_LOG` emits only the **last entry** plus any **same-session match** — not the
  full file. `REPEAT_PIN` is computed for you; trust it instead of re-scanning.
- `MEMORY` emits a `TAIL` for dedup awareness; full `CONTENT` appears only when
  `MIGRATION_NEEDED: yes`.
- If the script prints `ERROR: No project detected`, say so and stop — pin is project-scoped.

---

## Your role

Break checkpoint assistant. Work through the steps below. Step 1 is display-only — proceed immediately. Steps 2 and 3 are interactive — wait for the user's reply before proceeding.

---

## Step 0 — Ramp

Invoke `/ramp:pin` now using the Skill tool with no arguments. If the Skill tool returns an error or the skill is not found (ramp not installed), skip silently and proceed to Step 1. After ramp:pin completes its full flow, continue with Step 1.

---

## Step 1 — Status (display only)

Read the collected sections and render:

```
## Pin — [REPO] — [DATE]

Branch: [BRANCH]
Changes: [N files from CHANGES, listed] or "clean"

In Progress: [first task from IN_PROGRESS] or "(nothing)"
Up Next: [top tasks from UP_NEXT, one per line indented] or "(nothing)"
Plans: [N active, N marked for cleanup from PLANS] or "none"

Last snapshot: [LAST_SNAPSHOT] [+(SESSIONS_SINCE sessions) if > —] or "—"
Last session log: [LAST_SESSION_LOG] ([LOG_ENTRIES] entries) or "—"
Ramp: [RAMP line]  (omit if RAMP: no graph)
Toolbox: plugins [in sync / N stale / N missing / unavailable from PLUGIN_DRIFT]

---

### This session — [SESSION first 8 chars] · [TITLE]

**What happened:**
- [3–8 bullets synthesized from FILES_TOUCHED, GIT_LOG, and this conversation's activity]

**Files changed:** [comma-separated from FILES_TOUCHED, or "none"]
**Git:** [N commit(s) — "message of most recent" from GIT_LOG] or "none"
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

**Repeat-pin / skip check** (uses the `SESSION_LOG` section — do not re-scan the file):

- If `REPEAT_PIN: no` — this is the first pin for this session. Draft a full entry (below).
- If `REPEAT_PIN: yes` — prior entr(ies) for this session already exist (shown in full
  under `SAME_SESSION_ENTRIES`). Two cases:
  - **Nothing new:** the most recent commit in `GIT_LOG` matches the prior entry's
    `**Git:**` line **and** `FILES_TOUCHED` matches its `**Files changed:**` line (or both
    are "none"). Print `Nothing new since last pin — no-op.` and stop without writing.
  - **New activity:** draft only the *new* work since those entries (cross-reference the
    bullets in all `SAME_SESSION_ENTRIES` to avoid duplication) and use the header suffix
    given by `REPEAT_PIN` (e.g. `(2)`, `(3)`).

1. Draft a structured entry:
   ```
   ## [DATE] · [first 8 chars of SESSION]   ← append suffix from REPEAT_PIN if repeat
   **Files changed:** [comma-separated relative paths from FILES_TOUCHED, or "none"]
   **Git:** [N commit(s) — "message of most recent"] or "none"
   - [key action or decision — 3–8 bullets]
   **What didn't work:** [failed approach — "tried X, failed because Y"] (omit if none)
   **Resume:** [exact next step to take when picking this up] (omit if nothing in flight)
   **Open threads:** [blocker or deferred item] (omit section entirely if none)
   ```
2. Show the draft. Ask: "Save to session-log.md? Reply `yes` or edit inline."
3. On confirm: append to the `SESSION_LOG` `PATH`.
   - If state is MISSING: create with Write tool using `# [REPO] Session Log\n\n` header
   - If exists: append with Edit tool (match the tail of `LAST_ENTRY`, append `\n\n` + entry)
4. Cross-project: for each path in `CROSS_PROJECT_FILES`, append an attributed entry to that
   project's session-log.md (infer owning project from the absolute path prefix):
   ```
   ## [DATE] · [8-char session id] [← source-repo]
   **Cross-project work from [source-repo] session:**
   - [specific files/actions in this project]
   ```

Constraints:
- Append only — never overwrite existing entries
- Do NOT write to MEMORY.md — session history belongs in session-log.md only
- If FILES_TOUCHED is "none": note "No file changes detected" in the entry body

After saving the session log, run this single block (names the session, refreshes the maps):
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/post-save.py
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py | python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/update-project-map.py
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plan-map.py > /dev/null
```
`post-save.py` names the current session (if unnamed) and renames any other unnamed sessions
in scope. If its output contains `Renamed:` lines, append them as a compact note to your response.

Then proceed immediately to Step 3.

---

## Step 3 — Stable patterns (optional)

If `MIGRATION_NEEDED` is "yes": run the migration flow first (full MEMORY.md is in `CONTENT`) —
1. From `CONTENT`, extract all `## Session snapshot — YYYY-MM-DD` blocks (each ends at the next `##` or EOF)
2. Convert each to session-log format: `## YYYY-MM-DD (migrated)\n[bullets]\n`
3. Append to session-log.md (create with header if missing)
4. Remove snapshot blocks from MEMORY.md (preserve all other content)
5. Report: "Migrated [N] snapshot(s) to session-log.md · MEMORY.md now [M] lines."

Then automatically capture stable patterns in MEMORY.md (no prompt needed):
1. Look back at this conversation. Identify durable facts: key decisions, stable patterns, important file paths, conventions, architectural choices — anything a future session needs. Discard session narrative (that belongs in session-log), git commit details, and ephemeral mechanics. Use the `MEMORY` `CONTENT` (full file, unless flagged ⚠ LARGE) to avoid duplicating what's already recorded.
2. Draft a concise dated section (5–15 bullets):
   ```
   ## Session snapshot — [DATE] · [first 8 chars of SESSION]

   - [key insight or decision]
   ...
   ```
3. Show the draft to the user for awareness, then immediately append to MEMORY.md using the
   `MEMORY` `PATH` — no confirmation needed.
   - If state is MISSING: create with Write tool using `# [REPO] Memory\n\n` header
   - If exists: append with Edit tool
4. Report: "MEMORY.md updated ([N] lines)."

Constraints:
- Never overwrite existing MEMORY.md content — append only
- Never fabricate details not discussed in this session
- Do not include ramp knowledge-graph, XP, or level details — those belong in /ramp:snapshot
- If MODE is `global` (no project): say "No project detected — MEMORY.md is project-scoped. Run this from within a repo."

---

## Step 4 — Compact

After Step 3 completes (or is skipped), output this single line and nothing else:

> Pinned. Run `/compact` now.
