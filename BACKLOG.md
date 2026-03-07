# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

## Backlog

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

## Icebox

### Additional agents
- `review.md` — structured code review (Haiku, read-only diff analysis)
- `summarize.md` — given a session JSONL path, return a concise summary

### mcp/server.py — toolbox MCP server
- Stub. Potential: expose session search + cleanup ops as MCP tools
