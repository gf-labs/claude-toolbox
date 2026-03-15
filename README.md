# claude-toolbox

Personal Claude Code global toolbox — versioned commands, agents, scripts, hooks, and docs.

## Goals

- Version-control and distribute global Claude Code commands, scripts, agents, hooks, and docs
- Extract large inline bash blocks from commands into standalone, reusable Python scripts
- Distribute via the plugin system (gfl-marketplace) — commands namespaced as `/tools:*`

## Commands

| Command | Description |
|---------|-------------|
| `/tools:backlog`        | Add an item to BACKLOG.md from within Claude |
| `/tools:brief`          | Start-of-session orientation — branch, backlog, plans, recent activity; `/tools:brief [session-id]` to summarize a past session |
| `/tools:cleanup`        | Clean up old Claude session artifacts — preview, extract context, then delete |
| `/tools:doctor`         | Claude Code environment + project health check (scope-aware) |
| `/tools:pin`            | Break checkpoint — status display, session log, MEMORY.md update |
| `/tools:search-sessions`| Search session history by keyword |
| `/tools:wrap`           | End-of-session housekeeping — git check, plan cleanup, backlog review, done marker |

## Session lifecycle

```
[start of session]
  /tools:brief        — orient: branch, in-progress, last snapshot, plans, recent activity

[during session]
  work...
  /tools:pin          — break checkpoint: status + session log + optional MEMORY.md update
  /tools:backlog      — add a new item to BACKLOG.md mid-session

[end of session]
  /ramp:wrap          — knowledge graph harvest (if ramp installed)
  /tools:wrap         — full close-out ritual:
    Step 0: ramp check
    Step 1: session log   → skip if /tools:pin already run
    Step 2: git check     → surface uncommitted changes + unpushed commits
    Step 3: plan cleanup  → list plans, offer to mark done
    Step 4: backlog       → mark completed items done
    Step 5: memory health → warn if MEMORY.md approaching 200-line limit
    Step 6: done?         → optionally mark session for deletion

[periodic]
  /tools:cleanup           — delete old sessions, extract context to session-log.md + MEMORY.md
  /tools:search-sessions   — search session history by keyword
```

### Storage

| Store | Location | Loaded automatically? | Written by |
|-------|----------|-----------------------|------------|
| `MEMORY.md` | `~/.claude/projects/[key]/memory/MEMORY.md` | Yes (auto-memory, 200-line limit) | `/tools:snapshot` |
| `session-log.md` | `~/.claude/projects/[key]/memory/session-log.md` | No | `/tools:summarize`, `/tools:wrap`, `/tools:cleanup` |
| `CLAUDE.md` | `[repo]/CLAUDE.md` or `~/.claude/CLAUDE.md` | Yes (every session) | Manual |
| Plans | `~/.claude/plans/[name].md` | No | Manual / agents |
| Session files | `~/.claude/projects/[key]/[id].jsonl` | No | Claude Code |

## Structure

```
claude-toolbox/
├── commands/    # slash commands delivered as /tools:*
├── agents/      # subagents (e.g., explore)
├── scripts/     # Python scripts called by commands
├── hooks/       # hooks.json for plugin-registered hooks
├── mcp/         # stub for future MCP server
└── docs/        # architecture plan and references
```

## Install

1. Add `CLAUDE_TOOLBOX_ROOT` to your `~/.claude/settings.json`:
   ```json
   { "env": { "CLAUDE_TOOLBOX_ROOT": "/path/to/claude-toolbox" } }
   ```
2. Add this repo as a marketplace source and install:
   ```
   /plugin install tools@gfl-marketplace
   ```
3. Restart the session — commands are available as `/tools:*`.

## Extending

**New command**: create `commands/[name].md` with frontmatter (`description`, `allowed-tools`, optional `model`). Bump version in `.claude-plugin/plugin.json`, then reinstall.

**New script**: add `scripts/[name].py` (stdlib only — no third-party deps). Reference it from a command via `python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/[name].py`.

**New agent**: create `agents/[name].md` with frontmatter (`name`, `description`, `tools`, `model`, `color`). Bump version and reinstall.
