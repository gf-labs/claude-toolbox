# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

## Backlog

### backlog.md — add tasks to the backlog from within Claude
- **Size:** S
- `/backlog` with no args: adds the most recent task/session context to the backlog as a new item
- `/backlog add this to backlog` with text: adds a user-defined item to the backlog
- Writes to `BACKLOG.md` in the current project dir (or claude-toolbox if no project)

### tools:status — focus on current project, not knowledge tree
- **Size:** XS
- Replace the knowledge tree section with current-project context: branch, MEMORY.md health, active plans
- Knowledge tree info is low-value in status; save it for `ramp:tree`

### search-sessions.md — search session history without deleting
- **Size:** S
- Complement to `cleanup` filter mode: read-only session search by pattern
- Script: extract F1 block from `cleanup.md` into `collect-session-search.py`
- Command: return matching sessions with title + first/last prompt excerpt

### context.md — current session health
- **Size:** S
- Show: MEMORY.md line count + status, plans count, active session estimate
- Uses `collect-memory.py` (already exists) + simple git/plans queries

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

## Icebox

### Additional agents
- `review.md` — structured code review (Haiku, read-only diff analysis)
- `summarize.md` — given a session JSONL path, return a concise summary

### mcp/server.py — toolbox MCP server
- Stub. Potential: expose session search + cleanup ops as MCP tools
