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

### run-pipeline.py: git event source-prefix mismatch
- **Size:** S
- Git commit events are stored with `source: "git:<hash8>"` (from `git_override` block) rather than `source: "{source}:<hash>"` — a targeted reset (`--source X`) cannot identify and remove them; they persist as orphans in `events.jsonl` after reset
- Fix: change `git_override` to store `source: "{source}:git:{hash8}"` and update the staleness/by-project cleanup filters to match
- Also update the force-clear filter (pre-loop) and targeted reset JSONL rewrite to use the new prefix scheme

### run-pipeline.py: model selection per phase (Haiku for 2F/2H, Sonnet for 2G)
- **Size:** S
- **Done 2026-04-04** — `MODEL_2F = "claude-haiku-4-5-20251001"` and `MODEL_2G = "claude-sonnet-4-6"` constants in run-pipeline.py; `--model` overrides passed to child sessions

### run-pipeline.py: Batch API for 2F — 50% additional cost reduction
- **Size:** M
- 41 independent 2F jobs = ideal Batch API use case; 50% cost reduction vs. regular API
- With Haiku + Batch API: ~$14 → ~$7 for a full run
- Implementation: replace `subprocess.run(["claude", "-p", ...])` with direct Anthropic SDK batch submission; poll for completion; process results from batch output stream
- Tradeoff: async (minutes-to-hours latency); removes `--allowedTools` complexity since prompts go direct to API; removes child session startup overhead
- Blocks on: model selection item above (Batch API + Haiku compounds both savings)

### run-pipeline.py: incremental re-analysis — skip unchanged combos
- **Size:** M
- For subsequent export cycles, most combos won't have new threads; re-running all 41 wastes full cost
- Implementation: store `{rows: N, date: YYYY-MM-DD}` alongside `status: complete` in pipeline-state.json; on next run, compare extracted_count vs stored rows; skip if unchanged
- Expected savings: subsequent cycles cost $2-5 instead of $14-51 (90%+ reduction)

### run-pipeline.py: pipeline 2F → 2G (start synthesis as soon as project's 2F done)
- **Size:** M
- Currently: 2F 100% complete → 2G starts; slow combos block entire synthesis phase
- Optimization: after each `run_2f_combo` succeeds, check if all source combos for that project are complete → immediately submit `run_2g_project` to same executor
- Saves ~20-30% wall-clock time at no cost increase

### run-pipeline.py: replace `--re-analyze` scaffold with clean programmatic prompt
- **Size:** S
- Current prompt includes interactive-use noise ("Paste this into a new Claude session") and IMPORTANT OVERRIDES fighting the scaffold; cleaner prompt → better Haiku output
- Replace: build prompt directly from extracted file list + inlined template content; remove scaffold entirely from 2F
- Side effect: removes one `Read` tool call per session (template read eliminated)

### run-pipeline.py: reduce max_workers + add retry with backoff (2F/2G)
- **Size:** S
- First 2F run revealed: 6 concurrent `claude -p` sessions saturates rate limit; failed sessions return non-zero with empty stderr (rate limit signature); transient failures required 3 manual re-runs
- Fix: reduce `max_workers` from 6 → 3; add retry-once-with-30s-backoff for "No analysis files written" failures before declaring combo failed
- Also add jitter (random 0–5s delay) to session starts to prevent synchronized bursts

### run-pipeline.py: log child session stdout to per-combo debug files (2F/2G)
- **Size:** S
- `r.stdout` is currently discarded on `returncode == 0`; this hid the "Could you approve those reads?" message that explained the permission failure for 30+ sessions
- Fix: write `r.stdout` + `r.stderr` to `GENERATED/analysis-logs/source/project.txt` (or `synthesis-logs/`) regardless of success/failure; enables post-run auditing without re-running

### run-pipeline.py: pre-flight cost estimate for 2F/2G
- **Size:** S
- 2F run cost ~$50 unexpectedly; no pre-flight estimate existed; total extracted file size is a proxy for input token count
- Fix: add `--estimate` flag to 2F/2G that counts input tokens across all pending combos and prints projected cost at Sonnet 4.6 rates; exits before launching any sessions
- Threshold: warn if projected cost >$10, require `--confirm` if >$25

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

### Build `/tools:overview` — cross-project dashboard
- **Size:** S
- New command + `collect-overview.py` script; renders two panels: **Plans** (all `~/.claude/plans/*.md` grouped by project + status, extracted from title/status markers) and **Sessions** (filtered notable sessions grouped by project, excluding re-analysis/synthesize/delete-me noise)
- Must work equally well in single-project repos (scoped to current project) and multi-project directories (full cross-project view); use `_scope.py` to detect context and adjust grouping accordingly
- Replaces the manual work of listing plans and sessions separately
