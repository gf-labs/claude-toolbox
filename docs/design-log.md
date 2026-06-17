# Design Log

Living record of open questions, key decisions, and architectural learnings.
Add entries as they arise — don't wait for a formal session.

---

## Orientation Command Taxonomy

*Decided 2026-04-21*

Four commands answer re-entry questions. Differentiated by absence duration, mental context loaded, and intent:

| | `brief` | `status` | `recap` | `overview` |
|---|---|---|---|---|
| **When** | Cold start / long absence | Mid-stream, still warm | After stepping away briefly | Planning / prioritization |
| **Question** | "Get me back up to speed" | "Where am I right now?" | "What did I do recently?" | "What should I work on next?" |
| **Session log** | Last 3–5 entries (scales to absence) | Last entry only | All entries in window | No |
| **Backlog** | In Progress + Up Next | In Progress only | No | Highlights (top 3–5) |
| **Plans** | All active | No | No | All active + sequencing |
| **Architecture snapshot** | Yes (scales to absence) | No | No | No |
| **Git state** | Summary | Detailed (diff stat + hunk headers) | Commits in window | In-flight summary |
| **Recent activity** | Yes (collect-history.py) | No | Files touched in window | Recent work (last few sessions) |
| **Next step** | Suggested | Immediate | "Pick up here" (one line) | Full sequencing (3 tiers) |
| **Model** | Haiku | Haiku | Haiku | Sonnet |
| **Writes?** | No | No | No | No |

**Depth scaling (brief only):** ABSENCE_DAYS drives output depth automatically — no flag needed.
- < 2 days: last 1 session log entry, skip architecture + MEMORY.md
- 2–7 days: last 3 entries, brief architecture snapshot
- 7+ days or unknown: last 5 entries, full architecture, full MEMORY.md

**recap time window:** `--days N` (default 1) or `--hours N` for sub-day windows.

**Architectural distinction:** `brief` always includes project-state (backlog, plans, architecture); `recap` never does. The time window is `recap`'s only lens — it cannot substitute for `brief`.

**overview freshness:** cross-references last session log Resume/Open threads field when building the sequencing section — surfaces in-motion work at top of Now tier.

---

## Pipeline Design Log

---

## Open Questions

### Integration architecture

**Q: How should synthesis facts be routed to destination docs?**
~~Current state: all delta appended to a single `integration-target` file in a catch-all `## Additional Facts` block.~~
*Resolved: 2026-04-09* — Route-then-patch architecture: Haiku maps synthesis sections → destination files + headings (cached `route-map-{date}.json`); Sonnet patches each section-to-heading pair independently. See `_route_synthesis_sections` + `_integrate_section_into_doc` in `run-pipeline.py`.

**Q: Is "heading" a sufficient locator for integration?**
*Resolved: 2026-04-09* — The Sonnet patch prompt instructs the model to determine edit type dynamically (augment-prose / add-bullet / add-table-row / add-subsection) based on what it reads at the target heading. The router provides file + heading; the patcher decides the edit intent.

**Q: What should the integration target model be?**
*Resolved: 2026-04-09* — `CODEX_DOCS_DIRS[project]` is the primary source (points to the project's `docs/` dir). Fallback: `parent(INTEGRATION_TARGETS[project])`. The router scans all `.md` files in `docs/` via `_build_docs_manifest` — no per-project hardcoding needed beyond the dir path.

**Q: How should non-local projects be handled in integration?**
*Resolved: 2026-04-09* — `_integrate_synthesis` checks `docs_dir.exists()` before proceeding; prints `· integrate/{project}: docs dir not on disk — skipping` and returns `False` (non-fatal, convergence loop exits cleanly).

**Q: Should per-doc integration timestamps be tracked in state?**
*Resolved: 2026-04-09* — State key scheme changed to `synthesize / {project}/{dest_stem}/integrated` — one key per destination file. On rerun without `--force`, destinations already marked `COMPLETE` are skipped entirely (0 model calls). Synthesis mtime tracking not needed; state keys serve the same purpose.

**Q: How should conflicts be handled?**
*Resolved: 2026-04-09* — `_integrate_section_into_doc` returns `INTEGRATE_CONFLICT` when Sonnet outputs `· Conflict: ...`. The conflict is appended to `docs/threads/integration-conflicts.md` (created automatically). The state key is NOT marked complete — the destination remains pending for retry after manual resolution.

---

### Source data parsing

**Q: Is source data parsed once or per-project?**
Answer: per `{source}/{project}` pair, sequential. `run_index` loops `sources → projects → chunks`, calling `claude -p` once per chunk. State tracks completion per pair — re-runs skip completed pairs. 3 sources × N projects = up to 3N index sessions, all sequential, no parallelism.
*Resolved: 2026-04-09*

**Q: Should index/synthesize phases run in parallel?**
Currently sequential nested loops. Parallelism would speed up full-corpus runs significantly (especially index, which is embarrassingly parallel by source×project). Risk: state file writes would need locking. Not implemented.
*Resolved: 2026-04-14* — Stage-then-merge: `_index_extract_worker` runs extraction in parallel via `ThreadPoolExecutor(max_workers=4)`; serial merge phase handles all disk writes. `_quarantine_lock` for thread-safe rejected.jsonl writes. State + dedup stay in merge phase only.

---

### Soft-tag system

**Q: Does soft-tag generation still occur with the current architecture?**
Answer: yes. `run_index` sets `PhaseStatus.SOFT_TAG` for any project slug not in PROJECTS. `run_discover` clusters catch-all events to generate candidate slugs. `run_propose` surfaces them. The indexing step is unchanged by the 2026-04-09 refactor.
*Resolved: 2026-04-09*

**Q: What is the promotion path for a soft-tagged project that doesn't exist locally?**
Answer: today, there is none — promotion requires adding the slug to PROJECTS, cloning the repo, and running `index --project <slug> --force`. There's no mechanism to synthesize-only for non-local projects and defer integration.
*Open as of 2026-04-09*

**Q: What is the long-term semantic layer between events and synthesis?**
Current pipeline has no persistent knowledge layer — synthesis re-derives meaning from raw events on every run. Non-deterministic, expensive at scale, conflicts surface late (at integrate, not at index). Three candidates explored in `docs/knowledge-representation-tradeoffs.md` and `docs/knowledge-architecture-deep-design.md`:
1. `relations.jsonl` — lightweight hybrid; AI extracts typed edges (`contradicts`, `supersedes`, `references`) once at index; `staleness.json` is already a prototype of this pattern
2. Knowledge AST — path-addressable tree (`example.config.value`); conflicts become same-path collisions detectable structurally; repo docs become parallel projections of AST subtrees
3. Kùzu embedded graph — zero-dependency property graph; Cypher queries; ACID; same pattern as AST but with arbitrary edge types
*Open as of 2026-04-09; design documented*

---

## Key Decisions

### 2026-04-09 — Route-then-patch replaces catch-all EOF append
Integration now uses a two-phase model: Haiku routing call (cached) maps synthesis sections to destination files + headings; Sonnet patch calls compare one section vs. one heading and insert delta immediately after the heading. Facts go to the semantically correct doc; duplicates are found because prior-pass inserts are now in-section (findable). Max passes reduced from 6 → 2.

### 2026-04-09 — Unrouted sections create new docs (not skipped)
If Haiku cannot route a synthesis section to any existing doc, a filename is derived from the section title and a new doc is created. Pipeline metadata sections (staleness summary, open questions) are the only exceptions — they are skipped via a pattern filter. This ensures no synthesis content is silently dropped.

### 2026-04-09 — 3-value return distinguishes no-delta from conflict
`_integrate_section_into_doc` returns `INTEGRATE_EDITED` / `INTEGRATE_NO_DELTA` / `INTEGRATE_CONFLICT`. Both EDITED and NO_DELTA mark state complete (idempotent reruns). CONFLICT does not — it stays pending so the destination is retried after the conflict is manually resolved.

### 2026-04-09 — File-size as convergence signal (not stdout)
Parsing `r.stdout` for "no new content" string is unreliable — the model can print "✓" regardless of whether it wrote anything. File size before vs. after subprocess call is authoritative. `changed = size_after > size_before`.

### 2026-04-09 — Edit tool, not Write, for integration
`Write` overwrites the entire file. Integration must use `Edit` to append to existing content. The integration prompt explicitly instructs the model to use `Edit` for existing files.

### 2026-04-09 — Convergence loop compensates for large-context imprecision
With a single large comparison (full synthesis vs full master doc), the model misses items each pass. Multi-pass loop (up to 6) compensates by re-running until file stops growing. This is a workaround for the catch-all append model — section-targeted integration would eliminate the need for more than 1–2 passes.

### 2026-04-09 — Append delta block, not inline insertion
Current integration appends a `## Additional Facts` block at the bottom. Intentional as a first-pass approach — safe, auditable, non-destructive. The trade-off: duplicated content across passes; facts not in the right sections; harder to read. Inline section-targeted insertion is the right long-term approach.

### 2026-04-14 — Stage-then-merge for parallel index
Workers do only slow work (claude -p API calls); no shared state during parallel phase. All disk writes, dedup, routing review, and state updates happen in the serial merge phase. This preserves correctness of `written_event_ids` dedup (initialized after all workers complete) and keeps `input()` routing review calls serial. `_quarantine_lock` is the only synchronisation primitive needed.

### 2026-04-13 — Section regex must match ANY ## heading
`_route_synthesis_sections` and `_integrate_synthesis` split on `\n(?=## )` and match `^(## [^\n]+)`. Prior patterns (`## \d+\.` for numbered sections, `## Theme \d+:` for home/personal synthesis) were too narrow — plain `## Heading` synthesis produced zero sections and triggered 11 instant no-ops. The fix must be applied to both functions together.

### 2026-04-13 — _build_docs_manifest uses rglob
Flat `glob("*.md")` only found top-level docs. Projects with `docs/` subdirs (learn-music, venture-automation, etc.) had manifests that were missing nested files. `rglob("*.md")` with `threads/` exclusion and relative path entries is the correct pattern. Entries must be relative paths (not `.name`) so the router can construct full paths.

### 2026-04-05 — Immutable events.jsonl
`events.jsonl` is never cleared by any reset operation. `run_reset --source X` rewrites it with source-matching entries removed. Full reset clears only staleness + by-project (recomputable). This design decision prevents data loss and enables the append-only global timeline model.

### 2026-04-05 — Index phase keys survive reset
`state["phases"]["index"]` keys are not cleared by `run_reset`. Mirrors the permanence of `events.jsonl`. Use `--force` to re-index.

### 2026-04-05 — `python3 -u` required when piping
`python3 script.py | tee file.log` silently buffers stdout. `-u` forces unbuffered output. Required for any background pipeline run where output must be visible in real time.

### 2026-04-05 — BATCH_CHAR_CAP = 100_000
Each `claude -p` index call is capped at ~100k chars (~25k tokens). Oversized single files get their own chunk. Cap is a constant near the top of run-pipeline.py — adjust if model context limits change.

---

## Learnings

### Integration duplication root cause
The catch-all append model causes duplication because: (a) the model compares synthesis against the doc's original sections, not the prior-pass appended block; (b) it can't reliably identify its own prior output as "coverage." Solution: insert facts into the correct sections — the model can then find them on subsequent passes.

### Synthesis is not the source of truth
For projects with mature `docs/` directories (example-project, gfl), the existing docs may be *more complete* than the synthesis — they incorporate prior pipeline passes plus manual additions. Integration should always treat the existing docs as canonical and the synthesis as a delta source, never as a replacement.

### MCP pivot note (example-project)
The example-project MCP pivot is a post-thread Claude Code session idea from April 2026, not a formal decision recorded in the AI-ingested threads. Always note this distinction when referencing the pivot in synthesis or docs — it predates the ingested thread corpus.

### Git event source-prefix gap
Git commit events use `source: "git:<hash8>"`, not `source: "{source}:<hash>"`. Targeted reset (`--source X`) cannot remove them — they persist as orphans after a source reset. Known gap as of 2026-04-05.

### Section regex bugs cause silent data loss
When synthesis sections aren't matched by the split regex, the entire synthesis file appears as one section with no heading — the router maps it to a single destination or drops it entirely. No error is raised; the integrate run completes successfully with a no-op. Always test regex changes against actual synthesis output before running full integration.

### Synthesis is rarely the most current source for mature projects
For projects with active docs/ directories (example-project, gfl), existing docs may incorporate manual additions and prior pipeline passes that aren't in the current synthesis. The synthesis is a delta source, not a replacement. The integration approach (additive delta only, never wholesale replace) is the correct invariant.

### The compiler analogy clarifies the missing layer
The pipeline maps to compiler stages: conversations → events.jsonl (IR) → synthesis.md → repo docs. The current pipeline skips the AST — it regenerates "machine code" from IR on every run. The semantic layer (AST or relations graph) should be built once at index time and projected on demand. See `docs/knowledge-representation-tradeoffs.md`.
