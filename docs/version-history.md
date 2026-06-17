# claude-toolbox — Version History

Milestones compiled from git log. Patch-level fixes and doc-only commits omitted.

---

## v0.4.37 — 2026-04-14
**Parallel index — stage-then-merge**
- `_index_extract_worker(src, proj, files, known_projects, auto)` — runs all `claude -p` extraction calls for one `(src, proj)` task; returns result dict; makes zero disk writes
- `ThreadPoolExecutor(max_workers=_MAX_INDEX_WORKERS)` in `run_index` Phase 1; `as_completed` collects results
- Serial merge phase (Phase 2): `written_event_ids` dedup, routing review (`input()` calls), all disk writes, state updates — all moved out of workers
- `_quarantine_lock = threading.Lock()` — serialises concurrent rejected.jsonl writes from multiple workers sharing a source
- `_MAX_INDEX_WORKERS = 4` constant; `BATCH_CHAR_CAP` unchanged
- Projected speedup: 3–5× wall-clock on full-corpus index runs

## v0.4.36 — 2026-04-11 / 2026-04-13
**Integration hardening + repo topology fixes**
- Section split regex: `re.split(r'\n(?=## )')` + `re.match(r'^(## [^\n]+)')` — matches ANY `## ` heading; prior pattern (`## \d+\.` / `## Theme \d+:`) caused 11 instant no-ops on plain-heading synthesis files
- `_build_docs_manifest`: `glob("*.md")` → `rglob("*.md")` with `threads/` exclusion + relative path entries; unblocked repos with `docs/` subdirs (learn-music, etc.)
- `collect-history.py` PARENT mode bug fixed: `_parent_path` path-prefix matching replaces `c.name` basename matching; was showing "No Claude activity" despite daily work
- `projects.json`: `personal/personal` refs → `personal/self` (canonical); 32 integration targets added
- Repo namespace audit: `personal/self`, `_archive/` for retired repos, `business/` for active

## v0.4.35 — 2026-04-09
**integrate: route-then-patch architecture**
- Replaced catch-all EOF append with two-phase route-then-patch model
- Phase 1: Haiku maps synthesis sections → destination files + headings (cached `route-map-{date}.json`); `--route-only` flag for dry-run inspection
- Phase 2: Sonnet applies focused per-section edit immediately after target heading (not at EOF)
- Unrouted sections: derive filename from section title and create new doc (e.g. `example-doc.md`); pipeline metadata sections skipped
- Manifest validation: Haiku-proposed filenames validated against `docs/` manifest before any write (hallucination guard)
- Conflict logging: contradictions written to `docs/threads/integration-conflicts.md`; not marked complete until resolved
- State keys: changed from `{project}/integrated` (one) → `{project}/{dest_stem}/integrated` (one per destination file)
- `_INTEGRATE_MAX_PASSES` reduced 6 → 2; section-level comparisons converge in 1 pass
- Fallback: routing failure gracefully falls back to `_integrate_synthesis_legacy`
- `MODEL_INTEGRATE_ROUTE` (Haiku) + `MODEL_INTEGRATE_PATCH` (Sonnet) model aliases added

## v0.4.34 — 2026-04-09
**synthesize --integrate + convergence loop**
- `run_integrate()` — convergence loop; calls `_integrate_synthesis()` up to 6 passes until file stops growing
- `_integrate_synthesis()` — appends unique delta from synthesis to `integration-target` doc; file-size comparison as convergence signal
- `run_synthesize` gains `--integrate` flag; `run_pipeline` auto-calls integrate after synthesize
- `integrate` subcommand added to CLI (`--project`, `--force`)
- Fixed: state migration not persisted to disk (migrate-in-memory-only bug)
- Fixed: `run_reset()` was clearing stale `"ingest"` key instead of `"synthesize"`

## v0.4.33 — 2026-04-09
**Pipeline architecture refactor — all 15 phases (A–E, F, G)**

Phase A — Renames:
- `run_ingest` → `run_synthesize`; subcommand `ingest` → `synthesize`
- `run_artifacts` / `artifacts` → `run_preserve` / `preserve`
- `run_discover` / `discover` → `run_propose` / `propose`
- Constants renamed to match

Phase B — Orchestrator:
- `run` subcommand: `run --project P [--source S] [--force] [--auto]`
- Calls: `index → _classify_content → synthesize [→ preserve] [→ propose]`
- `codex` excluded from auto-run (requires human cluster-map review)

Phase C — projects.json:
- `~/Repos/archive/projects.json` externalizes PROJECTS, SOURCES, CATCHALL_PROJECTS, CODEX_DOCS_DIRS, INTEGRATION_TARGETS, STALE_GLOBS
- Script falls back to hardcoded values if file absent
- `auto-propose` fires when new events found for a project in the current index run

Phase D — Infrastructure:
- `_validate_event()` — required-field + range checks; failed events → `rejected.jsonl`
- `_merge_project_index()` + `_merge_staleness_to_disk()` — extracted helpers; replace inline write patterns
- `repaint` subcommand — recomputes staleness for all events without re-indexing
- `extract` subcommand — thin wrapper for all 6 `extract-threads.py` modes

Phase E — Utility subcommands:
- `status --json` machine-readable output
- `reset --source S` targeted source removal
- `validate` event integrity check
- `show-projects` list known projects + their index state

Phase F — Commands:
- `commands/pipeline.md` — full Tier 1/Tier 2 status display; calls `status --json`
- `commands/codex.md` — preserve → cluster → codex → integrate flow
- `commands/ingest.md` refactored: 3-step flow (extract → batch preview → batch execute)
- `commands/thread-pipeline.md` updated: v1→v2 path migration complete

Phase G — Docs:
- `docs/pipeline-runbook.md` updated
- `docs/timeline-architecture.md` updated
- `docs/archive/` — old pipeline design docs archived

## v0.4.25 — 2026-04-05 / 2026-04-06
**Index / synthesize / batch split + soft-tag discovery**
- Split monolithic `run_ingest` (2D-2H phases) into three distinct subcommands:
  - `index` — build verified timeline from all AI thread exports (batched per source/project)
  - `ingest` (later renamed `synthesize`) — deep analysis + synthesis from timeline; reads `by-project/{project}.json`
  - `batch` — ad-hoc ingestion for PDFs, notes, git repos (preserves original behavior)
- `run_discover` / `discover` subcommand — clusters catch-all project events via Haiku; writes `soft-tags.json`
- `soft-tags.json` at `timeline/soft-tags.json` — quarantine for unverified project slugs
- `_CATCHALL_PROJECTS` constant defines default scope for discover
- Promotion path: add slug to PROJECTS → `index --project <slug> --force`
- `BATCH_CHAR_CAP = 100_000` — chunked `claude -p` calls; prevents context overflow
- `-u` (unbuffered stdout) required on `python3 -u ... | tee` — discovered during background runs

## v0.4.24 — 2026-04-05
**Commands: /aside, brief extension support, pin skip check**
- `/tools:aside` — aside/tangent handler command
- `tools:brief` extension model: base command + `.claude/status.md` project extension
- `tools:pin` skip check — no-op if nothing new since last pin

## v0.4.23 (unlabeled) — 2026-04-04 / 2026-04-05
**Global timeline index — immutable events.jsonl + staleness layer**
- `events.jsonl` — append-only global event log; never cleared on reset
- `by-project/{project}.json` — pointer arrays (IDs only); recomputable
- `staleness.json` — derived layer keyed `"{event_id}|{project}"`; recomputable; decoupled from events
- `_paint_timeline()` — computes staleness without mutating event dicts
- `run_reset()` full: clears staleness + by-project, never events.jsonl
- `run_reset()` targeted (`--source X`): filtered JSONL rewrite of events.jsonl; removes matching by-project entries
- Multi-project event support: one record in events.jsonl, ID in multiple by-project files
- Per-project staleness divergence: compound `"{event_id}|{project}"` keys

## v0.4.20 — 2026-03-21
**Gemini HTML parser + pipeline updates**
- Gemini `.html` export parser added to `extract-threads.py`
- Pipeline updated to handle Gemini source alongside Claude and ChatGPT

## v0.4.18 — 2026-03-20
**Thread extraction pipeline — initial version**
- `scripts/extract-threads.py` — extraction worker; handles Claude/ChatGPT/Gemini exports
- Modes: `--scan`, `--extract`, `--peek-unnamed`, `--apply-routing`, `--quality-check`
- `scripts/run-pipeline.py` — initial orchestration layer; phases 2D–2H
- `docs/pipeline-runbook.md` — operational runbook
- `templates/analysis-template.md` — per-thread analysis template

## v0.4.10 — 2026-03-14
**Session summary in /tools:pin Step 1**
- Pin command now shows session activity summary inline (not just branch/backlog state)

## v0.4.7 — 2026-03-14
**Command consolidation**
- `audit` merged into `doctor`; `env` and `rename-sessions` retired
- Cleaner command surface

## v0.4.6 — 2026-03-14
**Rename logic standardization**
- Single rename script, uniform output across brief/pin/wrap

## v0.4.5 — 2026-03-14
**Session auto-rename during lifecycle**
- Auto-renames unnamed sessions during brief/pin/wrap

## v0.4.4 — 2026-03-14
**Session rename from context**
- `rename-sessions` command + `name-session --path` flag

## v0.4.3 — 2026-03-14
**User-invocable session summarizer**
- `/tools:summarize` command

## v0.4.2 — 2026-03-14
**Doctor command**
- `/tools:doctor` — global env base + toolbox integrity checks

## v0.4.1 — 2026-03-14
**Global base commands + agents**
- Review and summarize agents added

## v0.4.0 — 2026-03-14
**Linting infrastructure**
- `pyproject.toml`, lint-py hook, `Bash(python3 -m ruff)` permission

## v0.3.8 — 2026-03-14
**Hooks infrastructure + plan-map**
- Hooks: SessionStart, PostToolUse
- `.project-map` plans cache

## v0.3.7 / v0.3.6 / v0.3.5 — 2026-03-14
**brief consolidation; per-command model config**

## v0.3.4 — 2026-03-09
**Session auto-naming + orphaned/unscoped key display split**

## v0.3.3 — 2026-03-09
**brief enrichment**
- Session excerpts, plan previews, memory status, ramp integration

## v0.3.2 — 2026-03-09
**Plan tracking in .project-map**
- Plans section: creation/reference session tracking

## v0.3.1 — 2026-03-09
**Orphaned plugin cache detection**

## v0.2.9 — 2026-03-08
**Session lifecycle**
- `/tools:wrap` end-of-session command
- `session-log.md` — persistent session history
- `/tools:pin` consolidation of summarize + snapshot
- Scope-aware commands via `_scope.py`

## v0.1 — 2026-03-07
**Initial repo scaffold**
- Migrated 6 global commands from `~/.claude/commands/`
- Plugin delivery via `--plugin-dir`
- `docs/`, `scripts/`, `agents/`, `hooks/` structure
