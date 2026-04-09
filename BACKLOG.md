# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

(nothing)

## Backlog

### Evaluate community Claude Code resources for toolbox ideas
- **Size:** S
- **Done 2026-03-14** — reviewed both repos; findings applied and backlogged below
- Applied: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`, `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` (settings.json); `isolation: worktree` on plan + review agents

### `/aside` command — mid-task side question
- **Size:** XS
- **Done 2026-04-05** — created `commands/aside.md`; pure Markdown, no scripts; handles redirect and reveals-a-problem edge cases

### `spinnerTipsOverride` with `excludeDefault: true`
- **Size:** XS
- **Done 2026-04-05** — already present in `~/.claude/settings.json` (lines 102–109); no action needed

### Suggest-compact hook — tool-call counter
- **Size:** S
- **Redundant** — covered by the "Context checkpoint" rule in `~/.claude/CLAUDE.md` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`; hooks add overhead for a problem already solved
- PreToolUse hook on Edit/Write; maintains per-session tool-call counter in `/tmp/claude-tool-count-<sessionId>`
- At threshold (default 50, configurable via `CLAUDE_COMPACT_THRESHOLD` env var) emits compact suggestion to stderr; repeats every 25 calls
- Source: `scripts/hooks/suggest-compact.js` — affaan-m/everything-claude-code

### Cost tracker hook — per-session cost log
- **Size:** S
- **Removed** — no hook event exposes token usage; `/cost` command and Anthropic dashboard already cover this

### `/checkpoint` command — named in-session checkpoints
- **Size:** S
- **Disposition:** New command — too consequential to fold into `pin` (executes `git stash`/commit; explicit invocation required)
- Creates named checkpoints via `git stash`/commit + log entry to `.claude/checkpoints.log` (`date | name | git SHA`)
- Subcommands: `verify` (compare current state vs checkpoint: files changed, test delta), `list` (all checkpoints relative to HEAD)
- Source: `commands/checkpoint.md` — affaan-m/everything-claude-code

### PreCompact compaction log hook
- **Size:** S
- **Redundant** — `/tools:pin` is run before compacting (per the context checkpoint rule), so session log already captures the boundary; a separate compaction log adds little
- PreCompact hook; appends timestamped event to `~/.claude/sessions/compaction-log.txt`
- Also annotates the active session file with `[Compaction occurred at HH:MM]` so context loss is visible in session history
- Source: `scripts/hooks/pre-compact.js` — affaan-m/everything-claude-code

### Codemaps — token-lean architecture docs
- **Size:** M
- **Disposition:** Integrate into `/doctor` as check P9 (not a standalone command)
  - Detect: if `docs/CODEMAPS/` exists, check freshness headers; flag files older than 90 days as `[WARN]`
  - Fix: when user says `fix P9`, run the generation flow inline
- Generates/updates `docs/CODEMAPS/`: `architecture.md`, `backend.md`, `frontend.md`, `data.md`, `dependencies.md`
- Each file has a freshness header: `<!-- Generated: DATE | Files scanned: N | Token estimate: ~N -->`
- If diff >30% from previous version, shows diff and asks approval before overwriting
- Target: keep each codemap under 1000 tokens for efficient context loading
- Source: `commands/update-codemaps.md` — affaan-m/everything-claude-code

### Hook profile system — `TOOLBOX_HOOK_PROFILE` env var
- **Size:** M
- Wrap hook scripts with a profile-aware dispatcher; each hook declaration specifies which profiles it applies to (`minimal`, `standard`, `strict`)
- `TOOLBOX_DISABLED_HOOKS=comma,separated,ids` for individual hook suppression
- Useful for disabling linting/plan-map hooks in dev sessions without editing settings.json
- Source: `scripts/lib/hook-flags.js` — affaan-m/everything-claude-code

### Commit `CLAUDE_TOOLBOX_ROOT` export to dotfiles
- **Size:** XS
- `shellenv/exports` was updated with `export CLAUDE_TOOLBOX_ROOT="$HOME/Repos/gfl/claude-toolbox"` to fix `!cmd` context injection in brief/pin/wrap — needs to be committed in the dotfiles repo



### Upgrade `brief` model to Sonnet if parent-mode quality degrades
- **Size:** XS
- Evaluated 2026-03-14: keeping Haiku — task is template rendering (no reasoning), well-specified format; Haiku handles it well
- Watch for: parent mode with full multi-repo table after `!cmd` fix takes effect (dotfiles commit pending); if output is malformed or missing sections, upgrade `model:` in commands/brief.md to `claude-sonnet-4-6`

### Git workflow commands/agents
- **Size:** M
- Add a suite of git-focused commands and agents to the toolbox:
  - `/tools:commit` — stage, summarize diff, draft conventional commit message, confirm, commit; handles pre-commit hook failures gracefully
  - `/tools:pr` — review unpushed commits, draft PR title + body (summary + test plan), call `gh pr create`; checks for open draft PRs first
  - `commit` agent — subagent called by `/tools:commit`; read-only diff analyzer that returns a structured commit message suggestion
  - `pr` agent — subagent called by `/tools:pr`; reads commits + diff, returns PR title + body in structured format
  - `/tools:stash` — named stash management: list, create with description, pop by name, diff stash vs HEAD
  - `/tools:log` — formatted git log viewer: filter by author, date range, path; highlight commits touching a file; link to GitHub if remote is GitHub
- **Design principle:** commands are thin interactive wrappers; agents handle the read + draft work; user always confirms before write actions

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
- **On ice** — needs a concrete use case before building; low priority until one emerges

### Improve readability of lifecycle command output
- **Size:** S
- Plan previews in `/tools:brief` and `/tools:pin` show the first bullet of each plan file, which is often a code snippet or fragment that reads poorly out of context (e.g. `` `idle_prompt` — Claude is waiting for user input ``)
- Consider: show plan title only, extract a `purpose:` line from plan frontmatter, or pick the first prose bullet (skip code-heavy lines)

### Review Anthropic agent SDK repos for best practices
- **Size:** S
- Two official Anthropic repos surfaced as best practices references:
  - `https://github.com/anthropics/agent-sdk-workshop` — workshop materials for the Agent SDK
  - `https://github.com/anthropics/claude-agent-sdk-demos` — demo implementations using Claude Agent SDK
- Review both for patterns worth capturing in toolbox commands and hooks

### Review community Claude Code repos for hooks and tips
- **Size:** S
- Two community repos not yet mined for backlog items:
  - `https://github.com/shanraisshan/claude-code-hooks` — community hook collection
  - `https://github.com/ykdojo/claude-code-tips` — tips and tricks for Claude Code
- Review both for hooks, settings, or patterns worth adding to toolbox

### run-pipeline.py: state/filesystem divergence check subcommand
- **Size:** S
- Abnormal termination can leave analysis files written but state not marked complete; required manual Python one-liners to diagnose and patch
- Fix: add `run-pipeline.py check-state` subcommand that compares generated-data/analysis/ filesystem vs pipeline-state.json and reports/auto-fixes divergences

### Include current session summary in `brief` and `status`
- **Size:** S
- Both commands should surface a summary of the current session so Claude has immediate context on what's already been done this session
- Options: call `mcp__claude-toolbox__get_session_log` for the active session, or read the session JSONL directly and extract recent assistant turns
- Render as a "Session so far" section near the top of each command's output

### Make `pin` context-aware — audit activity since last pin
- **Size:** XS
- **Done 2026-04-05** — added skip check to Step 2 of `commands/pin.md`: if prior entry exists and git log + FILES_TOUCHED match, no-ops with short message

### Add project extension support to `brief` — `.claude/status.md` injection
- **Size:** XS
- **Done 2026-04-05** — added `**Project extension**` collect block and rendering instructions to `commands/brief.md`

### `brief` scope — directory-aware project inclusion
- **Size:** S
- Currently `brief` in parent/global mode includes all known projects regardless of cwd. Change to scope by directory:
  - Run from a specific repo (e.g. `business/claude-toolbox`) → single-project mode, no sub-project table
  - Run from a group dir (e.g. `business/` or `personal/`) → includes only projects whose paths are children of cwd
  - Run from `~` or a root-like dir → includes all projects found in `~` and its subdirectories (current behavior)
- Implementation: in `collect-status.py`, filter project rows by comparing each project's resolved disk path against `cwd`; emit only rows where `path.startswith(cwd)` (or exact match for single-repo mode)
- Should replace the current `_scope.py` PARENT/SINGLE toggle with a pure path-prefix filter; `_scope.py` can remain for other consumers

### run-pipeline.py: `artifacts` subcommand follow-up items
- **Done 2026-04-07** — `artifacts` subcommand implemented (295 lines); `MODEL_ARTIFACTS = claude-sonnet-4-6`; per-thread extraction + rollup into `code-reference.md`; analysis-template.md updated with Technical Artifacts section
- **example-project integration verified 2026-04-08** — full manual artifact pass complete; all 61 artifact files (13 claude, 12 chatgpt, 36 gemini) assessed; 2 unique appends written (constructRaindropFromYoutubePlaylistItem → marketplace-metering.md, RaindropClient + YouTubeClient → auth-connector-impl.md); manual process documented in pipeline-runbook.md Phase 4b
- **Next:** Run `artifacts` for gfl, example-personal, homelab; then manual Phase 4b pass per project using runbook
- **Known gaps:**
  - `--max-workers` not implemented (sequential only — each thread awaits Claude subprocess before next starts); parallelization could cut runtime from ~6 hrs to ~1 hr for large projects
  - No `--check` mode (unlike other subcommands); add divergence check for artifact files vs state keys

### run-pipeline.py: `codex` subcommand — implementation-detail extraction layer
- **Done 2026-04-08** — implemented two-pass architecture:
  - Pass 1 (cluster): Sonnet reads `code-reference.md` + existing docs list → writes `generated-data/codex/{project}/cluster-map.json` → user confirms interactively (or `--auto`)
  - Pass 2 (delta): one Sonnet call per cluster → reads existing destination + artifact sections → writes staging delta to `generated-data/codex/{project}/{dest_slug}.md`
- Design decisions locked in: input = `code-reference.md` rollup only; output = staging files (not direct repo writes); `MODEL_CODEX = claude-sonnet-4-6`; `CODEX_DOCS_DIRS` dict for 4 projects; state under "codex" phase
- Flags: `--project`, `--docs-dir`, `--force`, `--auto`, `--cluster-only`

### Build `/tools:overview` — cross-project dashboard
- **Size:** S
- New command + `collect-overview.py` script; renders two panels: **Plans** (all `~/.claude/plans/*.md` grouped by project + status, extracted from title/status markers) and **Sessions** (filtered notable sessions grouped by project, excluding re-analysis/synthesize/delete-me noise)
- Must work equally well in single-project repos (scoped to current project) and multi-project directories (full cross-project view); use `_scope.py` to detect context and adjust grouping accordingly
- Replaces the manual work of listing plans and sessions separately
