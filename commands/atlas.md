---
description: Cross-project atlas with an adaptive render — ≤4 projects in scope get detail cards, more get one aligned digest line each, grouped by domain. Facets projects · sessions · memory · plans · specs · plugins · claude.md; a bare run renders all of them except plugins (opt-in, machine-global). --dir NAME|PATH anchors the lens at any directory; --all = the whole machine; --project NAME inspects any project from anywhere; --stale lists orphaned/unscoped keys. Read-only inventory lens (use /tools:status or /tools:brief for a single-project deep view).
argument-hint: [facet ...] [--all] [--dir NAME|PATH] [--project NAME] [--stale] [--full|--compact]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Collect context

Run this once. It parses the arguments, resolves scope, dispatches to the backing
collectors, renders, and emits sectioned output. Do NOT re-run collectors, re-derive
enumeration, or re-render — print what it printed.

```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-atlas.py $ARGUMENTS
```

Output is delimited by `=== SECTION ===` markers:

| Section | Meaning |
|---------|---------|
| `=== REQUEST ===` | how the arguments parsed (FACETS/PROJECT/DIR/DEPTH/SCOPE/STALE). If it has an `ERRORS:` line, surface it and stop. |
| `=== ERROR ===` | `--project` or `--dir` did not resolve; show the message and stop. |
| `=== ATLAS ===` | the fully rendered atlas (emitted when ≥2 project facets are requested — including the bare default). First line is a `##` header; every other line is pre-aligned final text. |
| `=== PROJECTS ===` | (single-facet mode only) TSV from collect-status: `GROUP PROJECT BRANCH LOCAL_BRANCHES SESSIONS CHANGES LAST_COMMIT MEMORY_LINES MEMORY_STATUS BACKLOG_ITEMS LAST_SNAPSHOT SESSIONS_SINCE LAST_SESSION_LOG LOG_ENTRIES LAST_COMMIT_DATE`, plus `# ORPHANED_KEYS` / `# UNSCOPED_KEYS` blocks. |
| `=== SESSIONS ===` | (single-facet) TSV `PROJECT SESSION TITLE LAST_EVENT` — newest last-event first within each project; `—` = unnamed/no events. |
| `=== MEMORY ===` | (single-facet) same rows as PROJECTS — render the memory columns (MEMORY_LINES / MEMORY_STATUS / LAST_SNAPSHOT / LAST_SESSION_LOG / LOG_ENTRIES). |
| `=== PLANS ===` | (single-facet) plan inventory: `file.md  NL  [project]  Title` + `  → first bullet`. |
| `=== SPECS ===` | (single-facet) TSV `PROJECT KIND STATUS FILE TITLE` — in-repo docs/superpowers specs and plans; STATUS live/done. |
| `=== PLUGINS ===` | plugin cache drift / sync lines. |
| `=== CLAUDE.MD ===` | (single-facet) TSV `CONTAINER PROJECT CLAUDE_MD_DEPTH MEMORY_LINES MEMORY_STATUS CHAIN` — the ` » `-joined inheritance chain. |
| `=== STALE ===` | (only with `--stale`) `ORPHANED`/`UNSCOPED` key rows, or `(none)`. |

---

## Your role

Read-only viewport over a pre-rendered atlas. Render the sections in the order
emitted. No writes, no questions.

## Output format

- **ATLAS** — print the section's first line as-is (it is the markdown header), then
  print every remaining line **verbatim inside one fenced code block** (```text …
  ```). Do not re-wrap, re-align, reorder, summarize, or annotate — alignment and
  elapsed-time phrasing were already computed.
- **Single-facet sections** (exactly one project facet requested) — render compactly:
  - **PROJECTS** — group rows sharing a `GROUP` header under a bold `**<container>/**`
    label. Table columns: `Project | Branch | Sessions | Changes | Memory | Last log`.
    On `--full`, add `Local branches | Backlog | Snapshot | Sessions-since | Last commit`.
    Render `# ORPHANED_KEYS` / `# UNSCOPED_KEYS` as a trailing `Stale:` line.
  - **SESSIONS** — group by project: `[first 8 of SESSION] [TITLE] — [LAST_EVENT]`,
    newest 5 per project then `(+N more)`; every row on `--full`.
  - **MEMORY** — one line per project: `[project] — [MEMORY_LINES] [MEMORY_STATUS] ·
    snapshot [LAST_SNAPSHOT] · log [LAST_SESSION_LOG] ([LOG_ENTRIES])`.
  - **PLANS** — the plan lines as-is, first bullet indented.
  - **SPECS** — group by project: `[KIND] [TITLE] ([STATUS])`, live rows first.
  - **CLAUDE.MD** — one line per project: `[project] (depth N): chain`; flag
    `WARN`/`THIN`/`MISSING` memory inline.
- **PLUGINS** / **STALE** — print the lines as-is.
- Where a bare date appears in single-facet rows, append `(today)`/`(yesterday)`/
  `(N days ago)`.

## Constraints

- No writes of any kind.
- **Output ends at the last emitted line — no closing commentary, synthesis,
  observations, or next steps.** Nothing after the final fence or row.
- Render only what `collect-atlas.py` emitted; never re-run collectors or shell out
  beyond the single command above.
- Never use inline bang-backtick; the single collection command above is a fenced
  bash block.
