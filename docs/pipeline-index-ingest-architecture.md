# Pipeline Architecture: Index + Ingest

## Overview

The pipeline has two distinct concerns that should be separate commands:

1. **`index`** — scan all source data, extract timeline events, map to projects. Runs once per export cycle. Output is the verified source of truth.
2. **`ingest --project <P>`** — per-project deep analysis and synthesis, reading from the already-built timeline. Runs on demand per project.

The current `run_ingest` conflates both steps, skips the analysis layer, and lacks batching for large corpora. This architecture separates them cleanly.

---

## Step 1: `run-pipeline.py index`

**Purpose:** Build the global timeline index from all source data.

**Inputs:**
- `source-data/claude/extracted/` — extracted AI conversation threads (flat .md files)
- `source-data/chatgpt/extracted/` — same
- `source-data/gemini/extracted/` — same (489 files — requires batching)
- Git repos (optional) — git log as timeline events
- PDFs / notebooks (optional) — additional sources

**Batching strategy:**
- Use `INDEX.md` per source to group files by project
- Run one `claude -p` extraction session per source/project batch
- ~78 claude files, ~107 chatgpt files, ~489 gemini files — manageable in per-project chunks

**Process:**
1. Read `INDEX.md` for each source → build `{project: [file_paths]}` mapping
2. For each source/project batch: run `claude -p` to extract timeline events
3. Paint staleness across all events (`_paint_timeline`)
4. Write output files

**Outputs** (permanent — never cleared on reset):
```
archive/timeline/
  events.jsonl          # global append-only event log
  by-project/
    gfl.json            # array of event IDs
    example-project.json
    ...
  staleness.json        # "{event_id}|{project}" keyed; recomputable
```

**Idempotency:** track `index/{source}/{project}` in `pipeline-state.json`. Skip if complete unless `--force`.

**CLI:**
```bash
python3 run-pipeline.py index                          # all sources
python3 run-pipeline.py index --source claude          # one source
python3 run-pipeline.py index --source claude --project example-project  # one combo
python3 run-pipeline.py index --force                  # re-index everything
```

---

## Step 2: `run-pipeline.py ingest --project <P>`

**Purpose:** Per-project deep analysis and synthesis, using the timeline as source of truth.

**Prerequisite:** `index` must be complete for the project.

**Inputs:**
- `timeline/by-project/<P>.json` — event IDs for this project
- `timeline/events.jsonl` — full event records
- `timeline/staleness.json` — staleness layer
- `source-data/<source>/extracted/<file>` — original thread files (for deep analysis)
- `docs/analysis-template.md` — analysis prompt template

**Process:**
1. Read project's event list from timeline
2. Resolve events → source files (via `lineage` field)
3. Run deep analysis per source/project batch (`analysis-template.md` pattern, Haiku)
4. Run cross-source synthesis (2G pattern, Sonnet) — reads analysis files + timeline staleness
5. Write synthesis staging doc

**Outputs:**
```
generated-data/
  analysis/<source>/<project>/    # deep per-thread analysis files
  synthesis/<project>/            # staging docs for Phase 4 integration
```

**CLI:**
```bash
python3 run-pipeline.py ingest --project example-project           # all sources for example-project
python3 run-pipeline.py ingest --project example-project --source claude  # one source
python3 run-pipeline.py ingest --project example-project --force
```

---

## What changes from current code

| Current | New |
|---|---|
| `run_ingest(path, source)` | Split into `run_index(source, project)` + `run_ingest(project, source)` |
| Event extraction inline in `run_ingest` | Moves to `run_index` |
| `_paint_timeline`, staleness writes | Stays in `run_index` |
| Synthesis directly from events (no analysis) | `run_ingest` adds analysis layer before synthesis |
| No batching | `run_index` batches per source/project via INDEX.md |
| No per-project filter | Both commands support `--project` |
| `2f` / `2g` subcommands | Absorbed into `run_ingest` (same logic, cleaner interface) |

---

## What stays the same

- Timeline three-file structure (`events.jsonl`, `by-project/`, `staleness.json`)
- `_paint_timeline` staleness logic
- `MODEL_2F` (Haiku) for extraction/analysis, `MODEL_2G` (Sonnet) for synthesis
- `analysis-template.md` prompt pattern
- Phase 4 integration (manual — staging docs → repo docs)
- `pipeline-state.json` idempotency tracking

---

## Reset behavior

- `reset` (full) — archives `extracted/`, clears analysis/synthesis/quality state; **never clears `timeline/`**
- `reset --source <S>` — targeted; removes source entries from timeline indexes
- `index --force` — re-indexes; rewrites timeline entries for that source/project

---

## Open questions — resolved 2026-04-05

- **Does `index` handle non-extracted sources (PDFs, git repos, notebooks)?**
  No. `index` is AI-thread-only (reads from `source-data/{source}/extracted/` via INDEX.md).
  PDFs, git repos, and notebooks use `batch <path> --source <S>` — the renamed ad-hoc path.

- **Does `ingest` replace `2f`/`2g` entirely, or do both coexist?**
  Both coexist. `2f`/`2g` remain for the old extraction-first workflow (full reprocess scenario).
  `ingest --project <P>` is the new timeline-driven path — runs after `index`, not after `2f`.

- **Batching unit for gemini (489 files)?**
  Per-project batches via INDEX.md. `_parse_index_md("gemini")` groups files by destination slug;
  each `src/proj` batch is one `claude -p` session. No fixed N-file chunks needed.
