# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

(nothing)

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

### `collect-plugin-drift.py` blind to `--plugin-dir` plugins
- **Size:** XS
- Reads `enabledPlugins` from `settings.json` to find installed plugins; returns `NO_PLUGINS_ENABLED` when using `claude-dev` (which clears `enabledPlugins` and loads via `--plugin-dir` instead)
- Fix: detect `--plugin-dir` sessions via an env var or flag, or skip drift check gracefully with an informational message instead of `NO_PLUGINS_ENABLED`

### backlog.md — add tasks to the backlog from within Claude
- **Size:** S
- `/backlog` with no args: adds the most recent task/session context to the backlog as a new item
- `/backlog add this to backlog` with text: adds a user-defined item to the backlog
- Writes to `BACKLOG.md` in the current project dir (or claude-toolbox if no project)

### search-sessions.md — search session history without deleting
- **Size:** S
- Complement to `cleanup` filter mode: read-only session search by pattern
- Script: extract F1 block from `cleanup.md` into `collect-session-search.py`
- Command: return matching sessions with title + first/last prompt excerpt

### Per-command model configuration
- **Size:** S
- Haiku for `brief`, `status` (lightweight); Sonnet for `cleanup`, `pin`
- `audit` and `env` already have appropriate models set

### pyproject.toml + ruff for script linting
- **Size:** S
- Add `pyproject.toml` with `[tool.ruff]` + wire into toolbox audit
- Prerequisite for lightweight PostToolUse lint hook

### Lightweight PostToolUse lint hook
- **Size:** M
- Hook runs `ruff check` + `py_compile` on any `.py` touched by Edit/Write
- Depends on pyproject.toml + ruff item above

### ramp env extension (in sup repo)
- **Size:** S
- `sup/.claude/commands/env.md` — ramp-specific checks on top of `/tools:env`
- See `sup/BACKLOG.md` for detail

### settings: fix marketplace path case (in dotfiles)
- **Size:** XS
- `extraKnownMarketplaces.gfl-marketplace.source.path` has lowercase `r` in `repos/sup`
- Fix to `Repos/sup` — works on macOS but is factually wrong

### Standalone gfl-marketplace repo with URL sources
- **Size:** S
- Create `gf-labs/gfl-marketplace` — pure manifest repo, no plugin code
- Use URL sources to point at standalone repos (no symlinks required):
  ```json
  { "name": "ramp",  "source": { "source": "url", "url": "https://github.com/gf-labs/sup.git" } },
  { "name": "tools", "source": { "source": "url", "url": "https://github.com/gf-labs/claude-toolbox.git" } }
  ```
- Update `settings.json` `extraKnownMarketplaces.gfl-marketplace.source.path` to point at new repo
- Remove `sup/toolbox` symlink + revert marketplace.json in sup
- Enables clean distribution: each plugin repo is independent

### Expand audit rules + underlying dependencies
- **Size:** M
- Add checks: `pyproject.toml` present, lint rules defined, `BACKLOG.md` exists, design-docs referenced
- Define explicit dependency graph between audit checks (e.g., Check 10 depends on lint rules)

### Global `/doctor` command — base + project extension pattern
- **Size:** S
- Create `~/.claude/commands/doctor.md` — a global base command that defines the check framework: environment health, tool availability, config validity
- Each repo extends it via a local `.claude/commands/doctor.md` that sources the global base with `@~/.claude/commands/doctor.md` and adds project-specific checks (e.g., venv present, `.mcp.json` configured, dependencies installed)
- No native command inheritance in Claude Code — purely prompt engineering convention
- Open question: per-command extension via `@file` injection vs. per-section override; pick one approach and document as the pattern
- Prototype in `dotfiles` or `sup` first; generalize after

### Global command toolbox — audit, abstract, and extend
- **Size:** M
- Evaluate all commands across all projects (`~/.claude/commands/`, `.claude/commands/` in each repo, plugin commands) for abstraction opportunities
- Pattern to consider: a "base" command in `~/.claude/commands/` defines shared behavior; a project-local `.claude/commands/` file extends or overrides it — similar to class inheritance
- Questions to resolve: does Claude Code support command inheritance natively, or is this purely a prompt-engineering convention? What's the right granularity (per-command extension vs. per-section injection via `@file`)?
- Candidates for promotion to global scope: `doctor`, `audit`, `phase-status` (currently dotfiles-only)
- Candidates for base+extend pattern: `audit` (global base checks + per-repo additions)

## Icebox

### Additional agents
- `review.md` — structured code review (Haiku, read-only diff analysis)
- `summarize.md` — given a session JSONL path, return a concise summary

### mcp/server.py — toolbox MCP server
- Stub. Potential: expose session search + cleanup ops as MCP tools
