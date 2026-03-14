# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

### `hooks/hooks.json` — wire plugin hooks (SessionStart + PostToolUse)
- **Size:** XS
- `hooks/hooks.json` is empty — two hooks need wiring:
  1. **SessionStart**: `validate-env.py` already exists; validates `CLAUDE_TOOLBOX_ROOT` is set and points to a real dir
  2. **PostToolUse**: run `collect-plan-map.py` to keep `.project-map` current after every tool use — currently only updated manually via `wrap`/`brief` or the CLAUDE.md rename rule
- Note: if `CLAUDE_TOOLBOX_ROOT` is unset the `${}` expansion fails before scripts run — visible hook failure is acceptable for SessionStart; PostToolUse should fail silently
- Both hooks should be added together since hooks.json is currently empty

### `status.md` — add toolbox health section
- **Size:** S
- The ramp/knowledge-tree context block was removed but the planned replacement was never added
- Add to `commands/status.md` auto-collected context:
  ```
  **Toolbox env**: !printenv CLAUDE_TOOLBOX_ROOT 2>/dev/null && echo "(set)" || echo "NOT SET"
  **Plugin drift**: !python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plugin-drift.py 2>/dev/null || echo "unavailable"
  ```
- Add to single-mode output format: `**Toolbox:** CLAUDE_TOOLBOX_ROOT [set / NOT SET] · plugins: [in sync / N stale / N missing]`

### settings: fix marketplace path case (in dotfiles)
- **Size:** XS
- `extraKnownMarketplaces.gfl-marketplace.source.path` has lowercase `r` in `repos/ramp`
- Fix to `Repos/ramp` — works on macOS but is factually wrong

## Backlog

### Evaluate everything-claude-code for toolbox ideas
- **Size:** S
- Review https://github.com/affaan-m/everything-claude-code and identify patterns, commands, or utilities worth incorporating into this toolbox
- Look for: prompt patterns, hook ideas, workflow automations, command designs not yet covered here

### Auto-collected context blocks (`!cmd`) don't expand `settings.json` env vars
- **Size:** S
- Commands using `${CLAUDE_TOOLBOX_ROOT}` in `!` blocks receive raw templates instead of executed output — the `!` executor doesn't expand env vars defined in `settings.json["env"]`
- Affects: `status`, `history`, `doctor`, `cleanup` (any command using `${CLAUDE_TOOLBOX_ROOT}` in context blocks)
- `audit` works because it uses only plain shell commands with no env var references
- Fix options: (a) use `$HOME/Repos/gfl/claude-toolbox` literals instead of the var, (b) wrap in a shell that sources the env, or (c) rely on `CLAUDE_TOOLBOX_ROOT` being set in the shell environment rather than settings.json
- Workaround: LLM runs Bash tool calls manually — output is still correct but not hands-free

### `agents/plan.md` — implementation planner agent
- **Size:** S
- Agent: reads codebase, returns a structured phase-by-phase implementation plan; no writes
- Frontmatter: `name: plan`, `description: Implementation planner`, `tools: Glob, Grep, Read, Bash`, `model: claude-sonnet-4-6`, `color: yellow`
- Output format per phase: Goal (1 sentence) · Files to create/modify · Existing code to reuse · Dependencies on other phases · Verification section at end

### `.claude/commands/audit.md` — toolbox self-audit (project-scope)
- **Size:** S
- Local `/audit` command (not plugin-delivered) for toolbox-specific checks not in `/tools:audit`
- Checks: T1 script shebangs, T2 scripts referenced by commands, T3 BACKLOG non-placeholder, T4 hooks.json non-empty, T5 plugin.json completeness (name/version/description/author/license/keywords/category)
- Output: `[WARN]` / `[PASSED]` per check; close with "Run `/tools:audit` for universal checks"
- Note: T4 will pass immediately once hooks.json is wired (do that first)

### `collect-summarize.py` — CROSS_PROJECT_FILES emits `~/.claude/*` paths
- **Size:** XS
- Bug: `collect-summarize.py` includes paths like `~/.claude/knowledge-graphs/claude-code.md` in CROSS_PROJECT_FILES output — these are not project repos and trigger false cross-project session-log entries
- Fix: filter CROSS_PROJECT_FILES to exclude any path starting with `~/.claude/` (or `Path.home() / '.claude'`)

### `collect-plugin-drift.py` blind to `--plugin-dir` plugins
- **Size:** XS
- Reads `enabledPlugins` from `settings.json` to find installed plugins; returns `NO_PLUGINS_ENABLED` when using `claude-dev` (which clears `enabledPlugins` and loads via `--plugin-dir` instead)
- Fix: detect `--plugin-dir` sessions via an env var or flag, or skip drift check gracefully with an informational message instead of `NO_PLUGINS_ENABLED`

### README.md — Install and Extending sections
- **Size:** S
- README ends with "Private — not intended for general use" with no setup instructions
- Add after the Commands table:
  - **Install**: env var setup (`CLAUDE_TOOLBOX_ROOT` in `settings.json`), `/plugin install tools@gfl-marketplace`, restart session
  - **Extending**: new command (create `commands/[name].md`, bump version, reinstall), new script (`scripts/[name].py`, stdlib only), new agent (`agents/[name].md` with frontmatter)
- Remove the "Private" line

### `.project-map` — `Created: unknown` for renamed plans
- **Size:** XS
- Renaming a plan file breaks JSONL linkage — JSONL records the original filename; renamed file shows `Created: unknown` in `.project-map`
- Fix options: (a) scan for both original and current filenames when building the map, (b) write a rename record to the JSONL at rename time via `collect-plan-map.py`

### `/backlog` command — add tasks to the backlog from within Claude
- **Size:** S
- `/backlog` with no args: adds the most recent task/session context to the backlog as a new item
- `/backlog add this to backlog` with text: adds a user-defined item to the backlog
- Writes to `BACKLOG.md` in the current project dir (or claude-toolbox if no project)

### `brief` — generalized phase/roadmap context section
- **Size:** S
- Add an optional "Phase" section to `tools:brief` output when a project has a roadmap-style doc
- Source: `dotfiles/.claude/commands/phase-status.md` — reads `docs/todo.md` + `docs/bugs.md`, runs `git stash list`, reports phase/blockers/next action. **Not yet integrated into `/tools:brief`.**
- Generalization needed: current impl is tightly coupled to dotfiles-specific paths; needs configurable doc path (default `docs/todo.md`) and generic `## Phase N` / `## Roadmap` detection
- Approach: new `collect-phase.py` script detects roadmap doc, extracts current phase + blocker; `brief` renders as a "Phase:" line
- Note: `phase-status.md` should remain in dotfiles as a standalone command; this item is about surfacing a generalized version inside `brief`

### search-sessions.md — search session history without deleting
- **Size:** S
- Complement to `cleanup` filter mode: read-only session search by pattern
- Script: extract F1 block from `cleanup.md` into `collect-session-search.py`
- Command: return matching sessions with title + first/last prompt excerpt

### Per-command model configuration
- **Size:** S
- `brief` and `status` already set to Haiku (v0.3.3+)
- Remaining: set Sonnet for `cleanup`, `pin`, `wrap` (complex reasoning); Haiku for `done` (trivial); leave `audit` and `env` unset (default is fine)

### pyproject.toml + ruff for script linting
- **Size:** S
- Add `pyproject.toml` with `[tool.ruff]` + wire into toolbox audit
- Prerequisite for lightweight PostToolUse lint hook

### Lightweight PostToolUse lint hook
- **Size:** M
- Hook runs `ruff check` + `py_compile` on any `.py` touched by Edit/Write
- Depends on pyproject.toml + ruff item above; add after hooks.json is wired

### Standalone gfl-marketplace repo with URL sources
- **Size:** S
- Repo already exists at `~/Repos/_archive/gfl-marketplace`
- Remaining work: switch to URL sources pointing at standalone repos (no symlinks required):
  ```json
  { "name": "ramp",  "source": { "source": "url", "url": "https://github.com/gf-labs/ramp.git" } },
  { "name": "tools", "source": { "source": "url", "url": "https://github.com/gf-labs/claude-toolbox.git" } }
  ```
- Update `settings.json` `extraKnownMarketplaces.gfl-marketplace.source.path` to point at the archive repo
- Remove `ramp/toolbox` symlink + revert marketplace.json in ramp
- Enables clean distribution: each plugin repo is independent

### Expand audit rules + underlying dependencies
- **Size:** M
- Add checks: `pyproject.toml` present, lint rules defined, `BACKLOG.md` exists, design-docs referenced
- Define explicit dependency graph between audit checks (e.g., Check 10 depends on lint rules)

### Global commands — base + project extension pattern
- **Size:** M
- **Live defect:** `ramp/.claude/commands/doctor.md`, `dotfiles/.claude/commands/doctor.md`, `ramp/.claude/commands/audit.md`, `ramp/.claude/commands/cleanup.md` all reference `@~/.claude/commands/` includes — but `~/.claude/commands/` is empty, so all `@` includes resolve to nothing
- Fix: create global base commands in `~/.claude/commands/`:
  - `doctor.md` — core env health checks (source: toolbox `env.md`)
  - `audit.md` — universal repo checks (source: toolbox `audit.md`)
  - `cleanup.md` — session artifact cleanup (source: toolbox `cleanup.md`)
- Each repo's local command extends via `@file` injection + project-specific checks
- No native command inheritance — `@file` injection is the pattern; per-command extension (not per-section override)
- Commands audited 2026-03-14: ramp has audit/cleanup/doctor/status; dotfiles has audit/doctor/new-package/phase-status; `phase-status` needs generalization before global promotion (see `brief` phase item)

### Additional agents
- **Size:** S
- `agents/review.md` — structured code review (Haiku, read-only diff analysis)
- `agents/summarize.md` — given a session JSONL path, return a concise summary

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
