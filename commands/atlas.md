---
description: Cross-project atlas — current project + nested children by default; --dir NAME|PATH anchors the lens at any directory; --all for the whole machine. Facets projects · sessions · memory · plans · plugins · claude.md — a bare run renders all of them except plugins (opt-in, machine-global); inspect any project from anywhere with --project NAME. Read-only inventory lens (use /tools:status or /tools:brief for a single-project deep view).
argument-hint: [facet ...] [--all] [--dir NAME|PATH] [--project NAME] [--stale] [--full]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Collect context

Run this once. It parses the arguments, resolves scope, dispatches to the backing
collectors, and emits sectioned output. Do NOT re-run collectors yourself or re-derive
enumeration — render exactly what it prints.

```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-atlas.py $ARGUMENTS
```

Output is delimited by `=== SECTION ===` markers:

| Section | Meaning |
|---------|---------|
| `=== REQUEST ===` | how the arguments parsed (FACETS/PROJECT/DIR/DEPTH/SCOPE/STALE). If it has an `ERRORS:` line, surface it and stop. |
| `=== ERROR ===` | `--project` or `--dir` did not resolve; show the message and stop. |
| `=== PROJECTS ===` | TSV from collect-status: `GROUP PROJECT BRANCH LOCAL_BRANCHES SESSIONS CHANGES LAST_COMMIT MEMORY_LINES MEMORY_STATUS BACKLOG_ITEMS LAST_SNAPSHOT SESSIONS_SINCE LAST_SESSION_LOG LOG_ENTRIES`, plus `# ORPHANED_KEYS` / `# UNSCOPED_KEYS` blocks. |
| `=== SESSIONS ===` | TSV `PROJECT SESSION TITLE LAST_EVENT` — one row per session, newest last-event first within each project; `—` = unnamed/no events. |
| `=== MEMORY ===` | same rows — render the memory columns (MEMORY_LINES / MEMORY_STATUS / LAST_SNAPSHOT / LAST_SESSION_LOG / LOG_ENTRIES). |
| `=== PLANS ===` | plan inventory: `file.md  NL  [project]  Title` + `  → first bullet`. |
| `=== PLUGINS ===` | plugin cache drift / sync lines. |
| `=== CLAUDE.MD ===` | TSV `CONTAINER PROJECT CLAUDE_MD_DEPTH MEMORY_LINES MEMORY_STATUS CHAIN` — the ` » `-joined inheritance chain. |
| `=== STALE ===` | (only with `--stale`) `ORPHANED`/`UNSCOPED` key rows, or `(none)`. |

---

## Your role

Read-only cross-project atlas. Render the sections the dispatcher emitted, in the order
given. One screenful. No writes, no questions.

## Output format

Lead with a one-line header: `## Atlas — [SCOPE from REQUEST: subtree | dir | all | project] · [N projects] — [date]`.

Then, per emitted facet section, render:

- **PROJECTS** — group by container: for rows sharing a `GROUP` header, print a bold
  `**<container>/**` label then the child rows beneath. Table columns (compact default):
  `Project | Branch | Sessions | Changes | Memory | Last log`. On `--full`, add
  `Local branches | Backlog | Snapshot | Sessions-since | Last commit`. Render
  `# ORPHANED_KEYS` / `# UNSCOPED_KEYS` as a trailing `Stale:` line.
- **SESSIONS** — group by project: one line per session, `[first 8 of SESSION] [TITLE] — [LAST_EVENT]`.
  Compact default: the newest 5 per project, then `(+N more)`. `--full`: every row.
- **MEMORY** — one line per project: `[project] — [MEMORY_LINES] [MEMORY_STATUS] · snapshot [LAST_SNAPSHOT] · log [LAST_SESSION_LOG] ([LOG_ENTRIES])`.
- **PLANS** — the plan lines as-is, one per plan, first bullet indented.
- **PLUGINS** — the drift/sync lines as-is.
- **CLAUDE.MD** — one line per project: `[project] (depth N): chain` — render the ` » ` chain;
  flag `WARN`/`THIN`/`MISSING` memory inline.
- **STALE** — a short list of orphaned/unscoped keys with their reason.

**Depth:** `--compact` (default) = the digest above. `--full` = every column. If DEPTH is
`full` and there are many projects, note at the top that this is a large render.

**Elapsed time:** where a date appears, append `(today)`/`(yesterday)`/`(N days ago)`.

## Constraints

- No writes of any kind.
- Haiku only — keep it fast.
- Render only what `collect-atlas.py` emitted; never re-derive enumeration or shell out to
  other collectors yourself.
- Never use inline bang-backtick; the single collection command above is a fenced bash block.
