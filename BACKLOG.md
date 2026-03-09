# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

- **Plan review in /tools:wrap Step 3** — surface a relevance assessment (this session / stale / unrelated) before asking which to mark done; completed/stale plans should be renamed with `-delete-me` suffix (same deferred-deletion model as sessions) rather than deleted immediately; `/cleanup` picks them up on next run
- **`/tools:summarize`** — on-demand session summary; reads current session JSONL, extracts decisions made, files changed, commands run, and open threads; outputs a concise human-readable recap (~10 bullets); useful after waking up mid-session or before handing off; model: Haiku (read-only, pure extraction)

## Backlog

### `/tools:wrap` — end-of-session housekeeping ritual
- **Size:** S
- Structured close-out flow; run after `/ramp:wrap` (which handles knowledge-graph harvest)
- **Steps in order:**
  1. **Snapshot** — run the snapshot flow (draft → confirm → write to MEMORY.md); core step, always runs
  2. **Git check** — show uncommitted changes + unpushed commits; prompt "commit/push before closing?" (surface only, no auto-push)
  3. **Plan cleanup** — run `collect-plans.py`; list plans that look complete; offer to delete
  4. **Backlog review** — show In Progress + Up Next; ask "Any items completed this session? (reply with names or `skip`)"
  5. **Memory health** — warn if MEMORY.md ≥ 150 lines after snapshot
  6. **Done?** — ask "Mark this session for deletion? (`yes`/`no`)"; calls done logic if yes
- Prompt at step 0: "Did you run `/ramp:wrap` first? (`yes`/`skip`)" — skip if ramp not installed
- Relationship: `/ramp:wrap` → `/tools:wrap`; together they close the session lifecycle loop that opens with `/tools:brief`

### `/tools:brief` — start-of-session orientation
- **Size:** S
- Minimal, fast start-of-session snapshot; counterpart to `/tools:wrap`; supersedes the `context.md` backlog item
- **Output (single mode, one screen):**
  ```
  ## Brief — [repo] — [date]

  Branch: [branch] [ahead N / clean] · [N changes or "clean"]
  In Progress: [first item] or "(nothing)"
  Up Next: [first item] or "(nothing)"
  Last snapshot: [date] (+N sessions) or "—"
  Plans: [N active] or "none"
  MEMORY.md: [N lines] [OK / THIN / WARN]
  ```
- **Parent/global mode:** same roll-up table as `status` but without the history section — just git + backlog + snapshot columns; faster than full status
- Uses existing collect scripts: `_scope.py`, `collect-status.py` (for snapshot info), `collect-plans.py`, `collect-memory.py`; no new scripts needed
- Model: Haiku — read-only, pure formatting
- Session lifecycle: `/tools:brief` (start) → work → `/ramp:wrap` → `/tools:wrap` (end)

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
- Haiku for `history`, `status` (lightweight); Sonnet for `cleanup`, `snapshot`
- `audit` and `doctor` already have appropriate models set

### pyproject.toml + ruff for script linting
- **Size:** S
- Add `pyproject.toml` with `[tool.ruff]` + wire into toolbox audit
- Prerequisite for lightweight PostToolUse lint hook

### Lightweight PostToolUse lint hook
- **Size:** M
- Hook runs `ruff check` + `py_compile` on any `.py` touched by Edit/Write
- Depends on pyproject.toml + ruff item above

### ramp doctor extension (in sup repo)
- **Size:** S
- `sup/.claude/commands/doctor.md` — ramp-specific checks on top of `/tools:doctor`
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
