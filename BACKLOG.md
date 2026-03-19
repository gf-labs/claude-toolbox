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
- **Disposition:** New command — no existing command covers mid-task side questions
- Pure Markdown command, no scripts needed
- Freeze task state, answer in fixed format (`ASIDE: [question]\n\n[answer]\n\n— Back to task: [description]`), resume automatically; read-only during aside
- Edge cases: question reveals a problem → flag before resuming; question is a redirect → ask before switching
- Source: `commands/aside.md` — affaan-m/everything-claude-code

### `spinnerTipsOverride` with `excludeDefault: true`
- **Size:** XS
- Add to `~/.claude/settings.json`: `"spinnerTipsOverride": {"excludeDefault": true, "tips": [...]}`
- Replaces Anthropic's default loading tips with custom ones
- Source: `best-practice/claude-settings.md` — shanraisshan/claude-code-best-practice

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

### Include current session summary in `brief` and `status`
- **Size:** S
- Both commands should surface a summary of the current session so Claude has immediate context on what's already been done this session
- Options: call `mcp__claude-toolbox__get_session_log` for the active session, or read the session JSONL directly and extract recent assistant turns
- Render as a "Session so far" section near the top of each command's output
